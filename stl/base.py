import enum
import itertools
import logging
import math
from collections import abc
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Literal as L,  # noqa: N817
    SupportsIndex,
    TypeVar,
    cast,
    overload,
)

import numpy as np
import numpy.typing as npt
from python_utils import logger

if TYPE_CHECKING:  # pragma: no cover
    from types import EllipsisType
    from typing import Protocol

    # this won't be changing anytime soon, so safe to import here
    from numpy._typing import _ArrayLikeFloat_co, _ArrayLikeInt_co
    from typing_extensions import TypeAlias

    # pyrefly: ignore[invalid-inheritance]
    class _Logged(logger.LoggerProtocol, Protocol):  # pragma: no cover
        logger: logging.Logger

    _Dedupe: 'TypeAlias' = 'RemoveDuplicates | int'
    _ToAxis: 'TypeAlias' = npt.NDArray[np.integer] | abc.Sequence[int]
    _ToPoint: 'TypeAlias' = (
        float | abc.Sequence[float] | npt.NDArray[np.floating | np.integer]
    )
    _ToTranslation: 'TypeAlias' = (
        abc.Sequence[_ToPoint] | npt.NDArray[np.floating | np.integer]
    )

    # same as used by `np.ndarray.__getitem__`
    _ToIndex: 'TypeAlias' = (
        SupportsIndex | slice | EllipsisType | _ArrayLikeInt_co | None
    )
    _ToIndices: 'TypeAlias' = _ToIndex | tuple[_ToIndex, ...]

    # specific to 2-d arrays
    _ToSlice2_0: 'TypeAlias' = tuple[SupportsIndex, SupportsIndex]
    _ToSlice2_1: 'TypeAlias' = (
        int
        | np.integer
        | tuple[slice | EllipsisType, int]
        | tuple[int, slice | EllipsisType]
    )
    _ToSlice2_2: 'TypeAlias' = (
        slice
        | tuple[()]
        | tuple[slice, slice]
        | list[int]
        | npt.NDArray[np.integer]
        | EllipsisType
    )

_bool_1d: 'TypeAlias' = np.ndarray[tuple[int], np.dtype[np.bool_]]
_intp_1d: 'TypeAlias' = np.ndarray[tuple[int], np.dtype[np.intp]]
_u16_1d: 'TypeAlias' = np.ndarray[tuple[int], np.dtype[np.uint16]]
_u16_2d: 'TypeAlias' = np.ndarray[tuple[int, int], np.dtype[np.uint16]]
_f32_1d: 'TypeAlias' = np.ndarray[tuple[int], np.dtype[np.float32]]
_f32_2d: 'TypeAlias' = np.ndarray[tuple[int, int], np.dtype[np.float32]]
_f32_3d: 'TypeAlias' = np.ndarray[tuple[int, int, int], np.dtype[np.float32]]
_f64_2d: 'TypeAlias' = np.ndarray[tuple[int, int], np.dtype[np.float64]]

# {"normals": _float32_1d, "vectors": _float32_2d, "attr": _uint16_1d}
_data_1d: 'TypeAlias' = np.ndarray[tuple[int], np.dtype[np.void]]

#: When removing empty areas, remove areas that are smaller than this
AREA_SIZE_THRESHOLD: Final[L[0]] = 0
#: Vectors in a point
VECTORS: Final[L[3]] = 3
#: Dimensions used in a vector
DIMENSIONS: Final[L[3]] = 3


class Dimension(enum.IntEnum):
    #: X index (for example, `mesh.v0[0][X]`)
    X = 0
    #: Y index (for example, `mesh.v0[0][Y]`)
    Y = 1
    #: Z index (for example, `mesh.v0[0][Z]`)
    Z = 2


# For backwards compatibility, leave the original references
X: Final[L[Dimension.X]] = Dimension.X
Y: Final[L[Dimension.Y]] = Dimension.Y
Z: Final[L[Dimension.Z]] = Dimension.Z


class RemoveDuplicates(enum.Enum):
    """
    Choose whether to remove no duplicates, leave only a single of the
    duplicates or remove all duplicates (leaving holes).
    """

    NONE = 0
    SINGLE = 1
    ALL = 2

    @classmethod
    def map(cls, /, value: '_Dedupe') -> 'RemoveDuplicates':
        pass


_LoggedT = TypeVar('_LoggedT', bound='_Logged')


def logged(class_: type[_LoggedT]) -> type[_LoggedT]:
    # For some reason the Logged baseclass is not properly initiated on Linux
    # systems while this works on OS X. Please let me know if you can tell me
    # what silly mistake I made here

    pass


@logged
class BaseMesh(logger.Logged, abc.Mapping['_ToIndices', np.ndarray]):
    """
    Mesh object with easy access to the vectors through v0, v1 and v2.
    The normals, areas, min, max and units are calculated automatically.

    :param numpy.array data: The data for this mesh
    :param bool calculate_normals: Whether to calculate the normals
    :param bool remove_empty_areas: Whether to remove triangles with 0 area
            (due to rounding errors for example)

    :ivar str name: Name of the solid, only exists in ASCII files
    :ivar numpy.array data: Data as :func:`BaseMesh.dtype`
    :ivar numpy.array points: All points (Nx9)
    :ivar numpy.array normals: Normals for this mesh, calculated automatically
        by default (Nx3)
    :ivar numpy.array vectors: Vectors in the mesh (Nx3x3)
    :ivar numpy.array attr: Attributes per vector (used by binary STL)
    :ivar numpy.array x: Points on the X axis by vertex (Nx3)
    :ivar numpy.array y: Points on the Y axis by vertex (Nx3)
    :ivar numpy.array z: Points on the Z axis by vertex (Nx3)
    :ivar numpy.array v0: Points in vector 0 (Nx3)
    :ivar numpy.array v1: Points in vector 1 (Nx3)
    :ivar numpy.array v2: Points in vector 2 (Nx3)

    >>> data = np.zeros(10, dtype=BaseMesh.dtype)
    >>> mesh = BaseMesh(data, remove_empty_areas=False)
    >>> # Increment vector 0 item 0
    >>> mesh.v0[0] += 1
    >>> mesh.v1[0] += 2

    >>> # Check item 0 (contains v0, v1 and v2)
    >>> assert np.array_equal(
    ...     mesh[0], np.array([1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 0.0, 0.0, 0.0])
    ... )
    >>> assert np.array_equal(
    ...     mesh.vectors[0],
    ...     np.array([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0], [0.0, 0.0, 0.0]]),
    ... )
    >>> assert np.array_equal(mesh.v0[0], np.array([1.0, 1.0, 1.0]))
    >>> assert np.array_equal(
    ...     mesh.points[0],
    ...     np.array([1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 0.0, 0.0, 0.0]),
    ... )
    >>> assert np.array_equal(
    ...     mesh.data[0],
    ...     np.array(
    ...         (
    ...             [0.0, 0.0, 0.0],
    ...             [[1.0, 1.0, 1.0], [2.0, 2.0, 2.0], [0.0, 0.0, 0.0]],
    ...             [0],
    ...         ),
    ...         dtype=BaseMesh.dtype,
    ...     ),
    ... )
    >>> assert np.array_equal(mesh.x[0], np.array([1.0, 2.0, 0.0]))

    >>> mesh[0] = 3
    >>> assert np.array_equal(
    ...     mesh[0], np.array([3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0])
    ... )

    >>> len(mesh) == len(list(mesh))
    True
    >>> bool((mesh.min_ < mesh.max_).all())
    True
    >>> mesh.update_normals()
    >>> float(mesh.units.sum())
    0.0
    >>> mesh.v0[:] = mesh.v1[:] = mesh.v2[:] = 0
    >>> float(mesh.points.sum())
    0.0

    >>> mesh.v0 = mesh.v1 = mesh.v2 = 0
    >>> mesh.x = mesh.y = mesh.z = 0

    >>> mesh.attr = 1
    >>> bool((mesh.attr == 1).all())
    True

    >>> mesh.normals = 2
    >>> bool((mesh.normals == 2).all())
    True

    >>> mesh.vectors = 3
    >>> bool((mesh.vectors == 3).all())
    True

    >>> mesh.points = 4
    >>> bool((mesh.points == 4).all())
    True
    """

    #: - normals: :func:`numpy.float32`, `(3, )`
    #: - vectors: :func:`numpy.float32`, `(3, 3)`
    #: - attr: :func:`numpy.uint16`, `(1, )`
    dtype: ClassVar[np.dtype[np.void]] = np.dtype([
        ('normals', np.float32, (3,)),
        ('vectors', np.float32, (3, 3)),
        ('attr', np.uint16, (1,)),
    ]).newbyteorder('<')  # Even on big endian arches, use little e.

    speedups: Final[bool]
    name: Final['bytes | str']
    data: Final[_data_1d]

    _min: _f32_1d
    _max: _f32_1d
    _areas: _f32_2d
    _centroids: _f32_2d
    _units: _f32_2d

    def __init__(
        self,
        data: _data_1d,
        calculate_normals: bool = True,
        remove_empty_areas: bool = False,
        remove_duplicate_polygons: '_Dedupe' = RemoveDuplicates.NONE,
        name: 'bytes | str' = '',
        speedups: bool = True,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.speedups = speedups

        if remove_empty_areas:
            data = self.remove_empty_areas(data)

        if (
            RemoveDuplicates.map(remove_duplicate_polygons)
            is not RemoveDuplicates.NONE
        ):
            data = self.remove_duplicate_polygons(
                data, remove_duplicate_polygons
            )

        self.name = name
        self.data = data

        if calculate_normals:
            self.update_normals()

    @property
    def attr(self) -> _u16_2d:
        # https://github.com/numpy/numpy/pull/30261
        pass

    @attr.setter
    def attr(self, value: '_ArrayLikeInt_co', /) -> None:
        pass

    @property
    def normals(self) -> _f32_2d:
        # https://github.com/numpy/numpy/pull/30261
        pass

    @normals.setter
    def normals(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @property
    def vectors(self) -> _f32_3d:
        # https://github.com/numpy/numpy/pull/30261
        pass

    @vectors.setter
    def vectors(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @property
    def points(self) -> _f32_2d:
        pass

    @points.setter
    def points(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @property
    def v0(self) -> _f32_2d:
        pass

    @v0.setter
    def v0(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @property
    def v1(self) -> _f32_2d:
        pass

    @v1.setter
    def v1(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @property
    def v2(self) -> _f32_2d:
        pass

    @v2.setter
    def v2(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @property
    def x(self) -> _f32_2d:
        pass

    @x.setter
    def x(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @property
    def y(self) -> _f32_2d:
        pass

    @y.setter
    def y(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @property
    def z(self) -> _f32_2d:
        pass

    @z.setter
    def z(self, value: '_ArrayLikeFloat_co', /) -> None:
        pass

    @staticmethod
    def remove_duplicate_polygons(
        data: _data_1d,
        value: '_Dedupe' = RemoveDuplicates.SINGLE,
    ) -> _data_1d:
        pass

    @staticmethod
    def remove_empty_areas(data: _data_1d) -> _data_1d:
        # https://github.com/numpy/numpy/pull/30261
        pass

    def update_normals(
        self,
        update_areas: bool = True,
        update_centroids: bool = True,
    ) -> None:
        """Update the normals, areas, and centroids for all points"""
        normals: _f32_2d = np.cross(self.v1 - self.v0, self.v2 - self.v0)

        if update_areas:
            self.update_areas(normals)

        if update_centroids:
            self.update_centroids()

        self.normals[:] = normals

    def get_unit_normals(self) -> _f32_2d:
        pass

    def update_min(self) -> None:
        pass

    def update_max(self) -> None:
        pass

    def update_areas(self, normals: '_f32_2d | None' = None) -> None:
        if normals is None:
            normals = np.cross(self.v1 - self.v0, self.v2 - self.v0)

        areas = 0.5 * np.sqrt((normals**2).sum(axis=1))
        self._areas = areas.reshape((areas.size, 1))

    def update_centroids(self) -> None:
        self._centroids = np.mean([self.v0, self.v1, self.v2], axis=0)

    def check(self, exact: bool = False) -> bool:
        """Check the mesh is valid or not

        :param bool exact: Perform exact checks.
        """
        pass

    def is_closed(self, exact: bool = False) -> bool:  # pragma: no cover
        """Check the mesh is closed or not

        :param bool exact: Perform a exact check on edges.
        """
        pass

    def get_mass_properties(self) -> tuple[np.float32, _f32_1d, _f64_2d]:
        """
        Evaluate and return a tuple with the following elements:
          - the volume
          - the position of the center of gravity (COG)
          - the inertia matrix expressed at the COG

        Documentation can be found here:
        http://www.geometrictools.com/Documentation/PolyhedralMassProperties.pdf
        """
        pass

    def is_convex(self) -> bool:
        """Return True if the mesh is convex, False otherwise."""
        pass

    def update_units(self) -> None:
        pass

    @staticmethod
    def rotation_matrix(axis: '_ToAxis', theta: float) -> _f64_2d:
        """
        Generate a rotation matrix to Rotate the matrix over the given axis by
        the given theta (angle)

        Uses the `Euler-Rodrigues
        <https://en.wikipedia.org/wiki/Euler%E2%80%93Rodrigues_formula>`_
        formula for fast rotations.

        :param numpy.array axis: Axis to rotate over (x, y, z)
        :param float theta: Rotation angle in radians, use `math.radians` to
                     convert degrees to radians if needed.
        """
        pass

    def rotate(
        self,
        axis: '_ToAxis',
        theta: float = 0,
        point: '_ToPoint | None' = None,
    ) -> None:
        """
        Rotate the matrix over the given axis by the given theta (angle)

        Uses the :py:func:`rotation_matrix` in the background.

        .. note:: Note that the `point` was accidentaly inverted with the
           old version of the code. To get the old and incorrect behaviour
           simply pass `-point` instead of `point` or `-numpy.array(point)` if
           you're passing along an array.

        :param numpy.array axis: Axis to rotate over (x, y, z)
        :param float theta: Rotation angle in radians, use `math.radians` to
                            convert degrees to radians if needed.
        :param numpy.array point: Rotation point so manual translation is not
                                  required
        """
        pass

    def rotate_using_matrix(
        self,
        rotation_matrix: '_f32_2d | _f64_2d',
        point: '_ToPoint | None' = None,
    ) -> None:
        """
        Rotate using a given rotation matrix and optional rotation point

        Note that this rotation produces clockwise rotations for positive
        angles which is arguably incorrect but will remain for legacy reasons.
        For more details, read here:
        https://github.com/WoLpH/numpy-stl/issues/166
        """
        pass

    def translate(self, translation: '_ToTranslation') -> None:
        """
        Translate the mesh in the three directions

        :param numpy.array translation: Translation vector (x, y, z)
        """
        pass

    def transform(self, matrix: '_f32_2d | _f64_2d') -> None:
        """
        Transform the mesh with a rotation and a translation stored in a
        single 4x4 matrix

        :param numpy.array matrix: Transform matrix with shape (4, 4), where
                                   matrix[0:3, 0:3] represents the rotation
                                   part of the transformation
                                   matrix[0:3, 3] represents the translation
                                   part of the transformation
        """
        pass

    @property
    def min_(self) -> _f32_1d:
        """Mesh minimum value"""
        pass

    @min_.setter
    def min_(self, min_: _f32_1d, /) -> None:
        pass

    @property
    def max_(self) -> _f32_1d:
        """Mesh maximum value"""
        pass

    @max_.setter
    def max_(self, max_: _f32_1d, /) -> None:
        pass

    @property
    def areas(self) -> _f32_2d:
        """Mesh areas"""
        pass

    @areas.setter
    def areas(self, areas: _f32_2d, /) -> None:
        pass

    @property
    def centroids(self) -> _f32_2d:
        """Mesh centroids"""
        pass

    @centroids.setter
    def centroids(self, centroids: _f32_2d, /) -> None:
        pass

    @property
    def units(self) -> _f32_2d:
        """Mesh unit vectors"""
        pass

    @units.setter
    def units(self, units: _f32_2d, /) -> None:
        pass

    @overload
    def __getitem__(self, k: '_ToSlice2_0', /) -> np.float32: ...
    @overload
    def __getitem__(self, k: '_ToSlice2_1', /) -> _f32_1d: ...
    @overload
    def __getitem__(self, k: '_ToSlice2_2', /) -> _f32_2d: ...
    @overload
    def __getitem__(self, k: '_ToIndices', /) -> Any: ...
    def __getitem__(self, k: '_ToIndices', /) -> Any:
        return self.points[k]

    def __setitem__(self, k: '_ToIndices', v: '_ArrayLikeFloat_co', /) -> None:
        self.points[k] = v

    def __len__(self) -> int:
        return self.points.shape[0]

    # mappings iterate over keys, this iterates over values
    def __iter__(self) -> abc.Iterator[_f32_1d]:  # pyright: ignore[reportIncompatibleMethodOverride]
        yield from self.points

    def __repr__(self) -> str:
        return f'<Mesh: {self.name!r} {self.data.size} vertices>'

    def get_mass_properties_with_density(
        self,
        density: float,
    ) -> tuple[np.float32, np.float32, _f32_1d, _f64_2d]:
        # add density for mesh,density unit kg/m3 when mesh is unit is m
        pass
