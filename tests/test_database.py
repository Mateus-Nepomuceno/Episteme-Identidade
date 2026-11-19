import pytest
from sqlalchemy import select

from identidade.database import (
    criar_engine,
    normalizar_database_url,
    validar_schema,
)
from identidade.models import Usuario


def test_create_user(session):
    novo_usuario = Usuario(
        nome='joana',
        senha='senha_secreta',
        email='teste@teste.com',
        cpf='12345678900',
        telefone='(11) 99999-9999',
    )
    session.add(novo_usuario)
    session.commit()

    usuario = session.scalar(select(Usuario).where(Usuario.nome == 'joana'))

    assert usuario.nome == 'joana'


def test_normalizar_database_url():
    assert (
        normalizar_database_url('postgres://user:pass@host:5432/db')
        == 'postgresql+psycopg://user:pass@host:5432/db'
    )
    assert (
        normalizar_database_url('postgresql://user:pass@host:5432/db')
        == 'postgresql+psycopg://user:pass@host:5432/db'
    )
    assert (
        normalizar_database_url('postgresql+psycopg://user:pass@host:5432/db')
        == 'postgresql+psycopg://user:pass@host:5432/db'
    )
    assert (
        normalizar_database_url('sqlite:///database.db')
        == 'sqlite:///database.db'
    )


def test_validar_schema():
    assert validar_schema('identidade') == 'identidade'
    with pytest.raises(ValueError, match='Schema inválido'):
        validar_schema('identidade; DROP SCHEMA public;')


def test_criar_engine_postgres_com_schema():
    pg_sem_schema = criar_engine('postgresql://user:pass@localhost:5432/db')
    pg_com_schema = criar_engine(
        'postgresql://user:pass@localhost:5432/db', 'identidade'
    )
    assert pg_com_schema.dialect.name == 'postgresql'
    assert pg_com_schema.pool._pre_ping is True
    assert len(pg_com_schema.pool.dispatch.connect) == (
        len(pg_sem_schema.pool.dispatch.connect) + 1
    )
    pg_sem_schema.dispose()
    pg_com_schema.dispose()
