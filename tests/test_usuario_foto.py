from http import HTTPStatus
from uuid import uuid4

JPEG_VALIDO = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01'
PNG_VALIDO = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
WEBP_VALIDO = b'RIFF\x24\x00\x00\x00WEBPVP8 '
TAMANHO_EXCEDENTE = 2 * 1024 * 1024 + 1


def test_upload_foto_jpeg_sucesso(client, user, user_token):
    response = client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('foto.jpg', JPEG_VALIDO, 'image/jpeg')},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(user.id)
    assert data['tem_foto'] is True


def test_upload_foto_png_sucesso(client, user, user_token):
    response = client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('foto.png', PNG_VALIDO, 'image/png')},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['tem_foto'] is True


def test_upload_foto_webp_sucesso(client, user, user_token):
    response = client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('foto.webp', WEBP_VALIDO, 'image/webp')},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['tem_foto'] is True


def test_upload_foto_tipo_invalido_retorna_415(client, user, user_token):
    response = client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('doc.pdf', b'%PDF-1.4', 'application/pdf')},
    )

    assert response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


def test_upload_foto_magic_bytes_invalidos_retorna_415(
    client, user, user_token
):
    response = client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('falsa.png', JPEG_VALIDO, 'image/png')},
    )

    assert response.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


def test_upload_foto_arquivo_vazio_retorna_422(client, user, user_token):
    response = client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('vazia.png', b'', 'image/png')},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_upload_foto_maior_que_2mb_retorna_413(client, user, user_token):
    conteudo_grande = PNG_VALIDO + (b'a' * TAMANHO_EXCEDENTE)
    response = client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('grande.png', conteudo_grande, 'image/png')},
    )

    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


def test_upload_foto_sem_autenticacao_retorna_401(client, user):
    response = client.put(
        f'/usuarios/{user.id}/foto',
        files={'arquivo': ('foto.png', PNG_VALIDO, 'image/png')},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_upload_foto_outro_usuario_retorna_403(client, admin, user_token):
    response = client.put(
        f'/usuarios/{admin.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('foto.png', PNG_VALIDO, 'image/png')},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_upload_foto_admin_altera_terceiro_e_404_inexistente(
    client, user, admin_token
):
    ok_response = client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {admin_token}'},
        files={'arquivo': ('foto.png', PNG_VALIDO, 'image/png')},
    )
    assert ok_response.status_code == HTTPStatus.OK
    assert ok_response.json()['tem_foto'] is True

    not_found_response = client.put(
        f'/usuarios/{uuid4()}/foto',
        headers={'Authorization': f'Bearer {admin_token}'},
        files={'arquivo': ('foto.png', PNG_VALIDO, 'image/png')},
    )
    assert not_found_response.status_code == HTTPStatus.NOT_FOUND


def test_read_foto_sucesso_e_404(client, user, user_token):
    sem_foto = client.get(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
    )
    assert sem_foto.status_code == HTTPStatus.NOT_FOUND

    inexistente = client.get(
        f'/usuarios/{uuid4()}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
    )
    assert inexistente.status_code == HTTPStatus.NOT_FOUND

    client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('foto.webp', WEBP_VALIDO, 'image/webp')},
    )

    com_foto = client.get(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
    )
    assert com_foto.status_code == HTTPStatus.OK
    assert com_foto.content == WEBP_VALIDO
    assert com_foto.headers['content-type'] == 'image/webp'
    assert com_foto.headers['cache-control'] == 'no-store'


def test_read_foto_sem_autenticacao_retorna_401(client, user):
    response = client.get(f'/usuarios/{user.id}/foto')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_foto_sucesso_idempotente_e_permissoes(
    client, user, admin, user_token, admin_token
):
    sem_auth = client.delete(f'/usuarios/{user.id}/foto')
    assert sem_auth.status_code == HTTPStatus.UNAUTHORIZED

    proibido = client.delete(
        f'/usuarios/{admin.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
    )
    assert proibido.status_code == HTTPStatus.FORBIDDEN

    inexistente = client.delete(
        f'/usuarios/{uuid4()}/foto',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert inexistente.status_code == HTTPStatus.NOT_FOUND

    client.put(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
        files={'arquivo': ('foto.jpg', JPEG_VALIDO, 'image/jpeg')},
    )

    deletada = client.delete(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
    )
    assert deletada.status_code == HTTPStatus.OK
    assert deletada.json()['tem_foto'] is False

    apos_delete = client.get(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {user_token}'},
    )
    assert apos_delete.status_code == HTTPStatus.NOT_FOUND

    idempotente = client.delete(
        f'/usuarios/{user.id}/foto',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert idempotente.status_code == HTTPStatus.OK
    assert idempotente.json()['tem_foto'] is False


def test_fluxo_completo_sem_foto_e_put_cadastral_preserva_foto(client):
    cadastro = client.post(
        '/usuarios/',
        json={
            'nome': 'mariana',
            'email': 'mariana@exemplo.com',
            'cpf': '111.444.777-35',
            'telefone': '(11) 97777-7777',
            'senha': 'senha_segura',
            'matricula': '20260001',
        },
    )
    assert cadastro.status_code == HTTPStatus.CREATED
    usuario_criado = cadastro.json()
    assert usuario_criado['tem_foto'] is False

    login = client.post(
        '/auth/token',
        data={'username': '20260001', 'password': 'senha_segura'},
    )
    assert login.status_code == HTTPStatus.OK
    token = login.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    leitura = client.get(
        f'/usuarios/{usuario_criado["id"]}',
        headers=headers,
    )
    assert leitura.status_code == HTTPStatus.OK
    assert leitura.json()['tem_foto'] is False

    edicao_sem_foto = client.put(
        f'/usuarios/{usuario_criado["id"]}',
        headers=headers,
        json={
            'nome': 'mariana silva',
            'email': 'mariana@exemplo.com',
            'cpf': '111.444.777-35',
            'telefone': '(11) 97777-7777',
            'senha': 'senha_segura',
        },
    )
    assert edicao_sem_foto.status_code == HTTPStatus.OK
    assert edicao_sem_foto.json()['tem_foto'] is False

    upload = client.put(
        f'/usuarios/{usuario_criado["id"]}/foto',
        headers=headers,
        files={'arquivo': ('avatar.png', PNG_VALIDO, 'image/png')},
    )
    assert upload.status_code == HTTPStatus.OK
    assert upload.json()['tem_foto'] is True

    edicao_com_foto = client.put(
        f'/usuarios/{usuario_criado["id"]}',
        headers=headers,
        json={
            'nome': 'mariana souza',
            'email': 'mariana@exemplo.com',
            'cpf': '111.444.777-35',
            'telefone': '(11) 97777-7777',
            'senha': 'senha_segura',
        },
    )
    assert edicao_com_foto.status_code == HTTPStatus.OK
    assert edicao_com_foto.json()['tem_foto'] is True
