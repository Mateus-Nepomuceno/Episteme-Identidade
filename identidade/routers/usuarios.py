from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from identidade.database import get_session
from identidade.models import Usuario
from identidade.schemas import (
    Mensagem,
    UsuarioCreate,
    UsuarioPublic,
)
from identidade.security import (
    exigir_admin,
    get_current_user,
    get_password_hash,
)

router = APIRouter(prefix='/usuarios', tags=['usuarios'])

TAMANHO_MAXIMO_FOTO = 2 * 1024 * 1024
TAMANHO_CHUNK_FOTO = 64 * 1024
TAMANHO_CABECALHO_WEBP = 12
TIPOS_FOTO_PERMITIDOS = {'image/jpeg', 'image/png', 'image/webp'}


def _assinatura_imagem_valida(dados: bytes, content_type: str) -> bool:
    if content_type == 'image/jpeg':
        return dados.startswith(b'\xff\xd8\xff')
    if content_type == 'image/png':
        return dados.startswith(b'\x89PNG\r\n\x1a\n')
    if content_type == 'image/webp':
        return (
            len(dados) >= TAMANHO_CABECALHO_WEBP
            and dados[:4] == b'RIFF'
            and dados[8:TAMANHO_CABECALHO_WEBP] == b'WEBP'
        )
    return False


async def _ler_foto_com_limite(arquivo: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await arquivo.read(TAMANHO_CHUNK_FOTO):
        total += len(chunk)
        if total > TAMANHO_MAXIMO_FOTO:
            raise HTTPException(
                status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                detail='A foto deve ter no máximo 2 MB',
            )
        chunks.append(chunk)
    return b''.join(chunks)


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UsuarioPublic)
def create_usuario(
    usuario: UsuarioCreate, session: Annotated[Session, Depends(get_session)]
):
    db_user = session.scalar(
        select(Usuario).where(
            (Usuario.email == usuario.email) | (Usuario.cpf == usuario.cpf)
        )
    )

    if db_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email ou CPF já cadastrado',
        )

    db_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        cpf=usuario.cpf,
        telefone=usuario.telefone,
        senha=get_password_hash(usuario.senha),
        e_admin=False,
        matricula=usuario.matricula,
    )

    session.add(db_usuario)
    session.commit()
    session.refresh(db_usuario)

    return db_usuario


@router.get('/{usuario_id}', response_model=UsuarioPublic)
def read_usuario(
    usuario_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
):
    if current_user.id != usuario_id and not current_user.e_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Permissão negada'
        )

    usuario = session.scalar(select(Usuario).where(Usuario.id == usuario_id))

    if not usuario:
        raise HTTPException(status_code=404, detail='Usuário não encontrado')

    return usuario


@router.put('/{usuario_id}', response_model=UsuarioPublic)
def update_usuario(
    usuario_id: UUID,
    usuario: UsuarioCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
):
    db_usuario = session.scalar(
        select(Usuario).where(Usuario.id == usuario_id)
    )

    if not db_usuario:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Usuário não encontrado'
        )

    if current_user.id != usuario_id and not current_user.e_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Permissão negada'
        )

    if usuario.e_admin != db_usuario.e_admin and not current_user.e_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Apenas administradores podem alterar privilégios',
        )

    db_usuario.nome = usuario.nome
    db_usuario.email = usuario.email
    db_usuario.cpf = usuario.cpf
    db_usuario.telefone = usuario.telefone
    if current_user.e_admin and usuario.matricula is not None:
        db_usuario.matricula = usuario.matricula
    db_usuario.senha = get_password_hash(usuario.senha)
    db_usuario.e_admin = usuario.e_admin

    try:
        session.commit()
        session.refresh(db_usuario)
        return db_usuario
    except IntegrityError:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email ou CPF já cadastrados',
        )


@router.delete('/{usuario_id}', response_model=Mensagem)
def delete_usuario(
    usuario_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[Usuario, Depends(exigir_admin)],
):
    db_usuario = session.scalar(
        select(Usuario).where(Usuario.id == usuario_id)
    )

    if not db_usuario:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Usuário não encontrado'
        )

    session.delete(db_usuario)
    session.commit()

    return {'mensagem': 'Usuário deletado'}


@router.put('/{usuario_id}/foto', response_model=UsuarioPublic)
async def upload_foto_usuario(
    usuario_id: UUID,
    arquivo: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
):
    if current_user.id != usuario_id and not current_user.e_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Permissão negada'
        )

    db_usuario = session.scalar(
        select(Usuario).where(Usuario.id == usuario_id)
    )
    if not db_usuario:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Usuário não encontrado'
        )

    content_type = arquivo.content_type or ''
    if content_type not in TIPOS_FOTO_PERMITIDOS:
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail='Formato inválido. Envie JPEG, PNG ou WebP',
        )

    dados = await _ler_foto_com_limite(arquivo)
    if not dados:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail='Arquivo vazio',
        )

    if not _assinatura_imagem_valida(dados, content_type):
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail='Conteúdo do arquivo não corresponde a uma imagem válida',
        )

    db_usuario.foto_dados = dados
    db_usuario.foto_tipo = content_type
    session.commit()
    session.refresh(db_usuario)

    return db_usuario


@router.get('/{usuario_id}/foto')
def read_foto_usuario(
    usuario_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
):
    db_usuario = session.scalar(
        select(Usuario).where(Usuario.id == usuario_id)
    )
    if not db_usuario or db_usuario.foto_dados is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Foto não encontrada'
        )

    return Response(
        content=db_usuario.foto_dados,
        media_type=db_usuario.foto_tipo or 'application/octet-stream',
        headers={'Cache-Control': 'no-store'},
    )


@router.delete('/{usuario_id}/foto', response_model=UsuarioPublic)
def delete_foto_usuario(
    usuario_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
):
    if current_user.id != usuario_id and not current_user.e_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Permissão negada'
        )

    db_usuario = session.scalar(
        select(Usuario).where(Usuario.id == usuario_id)
    )
    if not db_usuario:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Usuário não encontrado'
        )

    db_usuario.foto_dados = None
    db_usuario.foto_tipo = None
    session.commit()
    session.refresh(db_usuario)

    return db_usuario
