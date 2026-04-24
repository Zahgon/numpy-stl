import datetime
import enum
import io
import os
import struct
import zipfile
from collections.abc import Generator
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Final,
    Literal as L,  # noqa: N817
    cast,
)
from xml.etree import ElementTree as ET

import numpy as np

from . import (
    __about__ as metadata,
    base,
)
from .utils import b

# NOTE: This is needed because pyright will otherwise complain about
# the `# type: ignore[assignment]` below.
# pyright: reportUnnecessaryTypeIgnoreComment=false

try:
    from . import _speedups
except ImportError:  # pragma: no cover
    _speedups = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from typing import Protocol, type_check_only

    from _typeshed import SupportsWrite
    from typing_extensions import Buffer, Self, Writer

    from .base import _data_1d

    _Name = bytes | str

    @type_check_only
    class _StatefulWriter(Writer[Buffer], Protocol):
        def tell(self) -> int: ...


class Mode(enum.IntEnum):
    #: Automatically detect whether the output is a TTY, if so, write ASCII
    #: otherwise write BINARY
    AUTOMATIC = 0
    #: Force writing ASCII
    ASCII = 1
    #: Force writing BINARY
    BINARY = 2


# For backwards compatibility, leave the original references
AUTOMATIC: Final[L[Mode.AUTOMATIC]] = Mode.AUTOMATIC
ASCII: Final[L[Mode.ASCII]] = Mode.ASCII
BINARY: Final[L[Mode.BINARY]] = Mode.BINARY

#: Amount of bytes to read while using buffered reading
BUFFER_SIZE: Final[L[4096]] = 4096
#: The amount of bytes in the header field
HEADER_SIZE: Final[L[80]] = 80
#: The amount of bytes in the count field
COUNT_SIZE: Final[L[4]] = 4
#: The maximum amount of triangles we can read from binary files
MAX_COUNT: Final[float] = 1e8
#: The header format, can be safely monkeypatched. Limited to 80 characters
HEADER_FORMAT: Final[str] = '{package_name} ({version}) {now} {name}'


class BaseStl(base.BaseMesh):
    @classmethod
    def load(
        cls,
        fh: IO[Any],
        mode: Mode = AUTOMATIC,
        speedups: bool = True,
    ) -> 'tuple[bytes, _data_1d] | Any':
        """Load Mesh from STL file

        Automatically detects binary versus ascii STL files.

        :param file fh: The file handle to open
        :param int mode: Automatically detect the filetype or force binary
        """
        pass

    @classmethod
    def _load_binary(
        cls,
        fh: IO[bytes],
        header: bytes,
        check_size: bool = False,
    ) -> tuple[bytes, '_data_1d']:
        # Read the triangle count
        pass

    @staticmethod
    def _ascii_reader(  # noqa: C901
        fh: IO[bytes], header: bytes
    ) -> Generator[
        'bytes | tuple[list[float], tuple[bytes, bytes, bytes], int]',
        None,
        None,
    ]:
        pass

    @classmethod
    def _load_ascii(
        cls,
        fh: IO[bytes],
        header: bytes,
        speedups: bool = True,
    ) -> tuple[bytes, '_data_1d']:
        # Speedups does not support non file-based streams
        pass

    def save(  # noqa: C901
        self,
        filename: '_Name',
        fh: 'IO[bytes] | None' = None,
        mode: 'Mode | int' = AUTOMATIC,
        update_normals: bool = True,
    ) -> None:
        """Save the STL to a (binary) file

        If mode is :py:data:`AUTOMATIC` an :py:data:`ASCII` file will be
        written if the output is a TTY and a :py:data:`BINARY` file otherwise.

        :param str filename: The file to load
        :param file fh: The file handle to open
        :param int mode: The mode to write, default is :py:data:`AUTOMATIC`.
        :param bool update_normals: Whether to update the normals
        """
        assert filename, 'Filename is required for the STL headers'
        if update_normals:
            self.update_normals()

        if mode is AUTOMATIC:
            # Try to determine if the file is a TTY.
            if fh:
                try:
                    if os.isatty(fh.fileno()):  # pragma: no cover
                        write = self._write_ascii
                    else:
                        write = self._write_binary
                except OSError:
                    # If TTY checking fails then it's an io.BytesIO() (or one
                    # of its siblings from io). Assume binary.
                    write = self._write_binary
            else:
                write = self._write_binary
        elif mode is BINARY:
            write = self._write_binary
        elif mode is ASCII:
            write = self._write_ascii
        else:
            raise ValueError(f'Mode {mode!r} is invalid')

        if isinstance(fh, io.TextIOBase):
            # Provide a more helpful error if the user mistakenly
            # assumes ASCII files should be text files.
            raise TypeError(
                'File handles should be in binary mode - even when'
                ' writing an ASCII STL.'
            )

        name = self.name
        if not name:
            name = os.path.split(filename)[-1]

        try:
            if fh:
                write(fh, name)
            else:
                with open(filename, 'wb') as fh:
                    write(fh, name)
        except OSError:  # pragma: no cover
            pass

    def _write_ascii(self, fh: IO[bytes], name: '_Name') -> None:
        pass

    def get_header(self, name: '_Name') -> str:
        # Format the header
        pass

    def _write_binary(
        self,
        fh: '_StatefulWriter | io.TextIOWrapper',
        name: '_Name',
    ) -> None:
        pass

    @classmethod
    def from_file(
        cls,
        filename: str,
        calculate_normals: bool = True,
        fh: 'IO[bytes] | None' = None,
        mode: Mode = Mode.AUTOMATIC,
        speedups: bool = True,
        **kwargs: Any,
    ) -> 'Self':
        """Load a mesh from a STL file

        :param str filename: The file to load
        :param bool calculate_normals: Whether to update the normals
        :param file fh: The file handle to open
        :param dict kwargs: The same as for :py:class:`stl.mesh.Mesh`

        """
        pass

    @classmethod
    def from_multi_file(
        cls,
        filename: str,
        calculate_normals: bool = True,
        fh: 'IO[bytes] | None' = None,
        mode: Mode = Mode.AUTOMATIC,
        speedups: bool = True,
        **kwargs: Any,
    ) -> Generator['Self', None, None]:
        """Load multiple meshes from a STL file

        Note: mode is hardcoded to ascii since binary stl files do not support
        the multi format

        :param str filename: The file to load
        :param bool calculate_normals: Whether to update the normals
        :param file fh: The file handle to open
        :param dict kwargs: The same as for :py:class:`stl.mesh.Mesh`
        """
        pass

    @classmethod
    def from_files(
        cls,
        filenames: 'list[str]',
        calculate_normals: bool = True,
        mode: Mode = Mode.AUTOMATIC,
        speedups: bool = True,
        **kwargs: Any,
    ) -> 'Self':
        """Load multiple meshes from STL files into a single mesh

        Note: mode is hardcoded to ascii since binary stl files do not support
        the multi format

        :param list(str) filenames: The files to load
        :param bool calculate_normals: Whether to update the normals
        :param file fh: The file handle to open
        :param dict kwargs: The same as for :py:class:`stl.mesh.Mesh`
        """
        pass

    @classmethod
    def from_3mf_file(
        cls,
        filename: str,
        calculate_normals: bool = True,
        **kwargs: object,
    ) -> Generator['Self', None, None]:
        pass


if TYPE_CHECKING:

    def StlMesh(  # noqa: N802
        filename: str,
        calculate_normals: bool = True,
        fh: 'IO[bytes] | None' = None,
        mode: Mode = Mode.AUTOMATIC,
        speedups: bool = True,
        **kwargs: Any,
    ) -> BaseStl: ...

else:
    StlMesh = BaseStl.from_file
