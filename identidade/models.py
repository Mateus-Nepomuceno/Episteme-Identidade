from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_as_dataclass, mapped_column, registry

table_registry = registry()


@mapped_as_dataclass(table_registry)
class Usuario:
    __tablename__ = 'usuarios'

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, init=False
    )
    nome: Mapped[str]
    senha: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    cpf: Mapped[str]
    telefone: Mapped[str]
    criado_em: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    e_admin: Mapped[bool] = mapped_column(default=False)
    matricula: Mapped[str | None] = mapped_column(unique=True, default=None)
    foto_dados: Mapped[bytes | None] = mapped_column(
        LargeBinary, default=None, nullable=True
    )
    foto_tipo: Mapped[str | None] = mapped_column(
        String(50), default=None, nullable=True
    )

    @property
    def tem_foto(self) -> bool:
        return self.foto_dados is not None
