# Copyright 2024 Kin-Chung (Ryan) Wong
# All rights reserved.
#
# THIS IS NOT FREE SOFTWARE. You may not use this file except with written permission
# from the original author(s).
#
# THE SOFTWARE SOURCE CODE IS MADE AVAILABLE FOR PUBLIC VIEWING “AS IS”, WITHOUT
# WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF 
# OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from collections.abc import Iterable
from functools import lru_cache
from typing import TypeVar, Generic, Union, Final, Any, Optional

_T = TypeVar("_T")

class ChunkList(Generic[_T]):
    _BITS = 7
    _MASK = 127
    _CHUNKSIZE = 128
    _LEVELS = 3
    _data: Final[list[list[list[_T]]]]
    _pool: Final[list[list[Any]]]
    _start: int
    _stop: int

    def __init__(self) -> None:
        self._data = self._pool_getnew()
        self._pool = []
        self._start = 0
        self._stop = 0

    def append(self, item: _T) -> int:
        """Appends the item to the right side of the ChunkList,
        and returns the assigned index of the item.

        Post-conditions:
            The first item in the list will be assigned index 0,
            and each item thereafter will be assigned the next index.
            The returned index value does not wraparound.
        """
        (idx, self._stop) = (self._stop, self._stop + 1)
        self.put(idx, item)
        return idx

    def put(self, idx: int, item: Optional[_T]) -> None:
        _, k1, k2, k3 = self._decompose(idx)
        ### TODO optimize later
        if self._data[k1] is None:
            self._data[k1] = self._pool_get()
        if self._data[k1][k2] is None:
            self._data[k1][k2] = self._pool_get()
        self._data[k1][k2][k3] = item

    def get(self, idx: int) -> Optional[_T]:
        if not (self._start <= idx < self._stop):
            return None
        _, k1, k2, k3 = self._decompose(idx)
        if self._data[k1] is None:
            return None
        if self._data[k1][k2] is None:
            return None
        return self._data[k1][k2][k3]
    
    def keyrange(self) -> range:
        return range(self._start, self._stop)

    def enumerate(self, _slice: Union[slice, range, Iterable[int]] = None) -> Iterable[tuple[int, _T]]:
        if _slice is None:
            _slice = self.keyrange()
        if isinstance(_slice, (slice, range)) and _slice.step in (None, 1):
            start = _slice.start
            if start is None:
                start = self._start
            elif start < 0:
                start += self._stop
            stop = _slice.stop
            if stop is None:
                stop = self._stop
            elif stop < 0:
                stop += self._stop
            start = max(start, self._start)
            stop = min(stop, self._stop) 
            if not (start < stop):
                return
            for idx in range(start, stop):
                yield (idx, self.get(idx))
            return
        if isinstance(_slice, slice):
            _slice = range(_slice.start, _slice.stop, _slice.step)
        if isinstance(_slice, Iterable):
            for idx in _slice:
                if (self._start <= idx < self._stop):
                    yield (idx, self.get(idx))
        else:
            raise Exception(f"{self.__class__.__qualname__}.enumerate() cannot interpret {repr(_slice)} as slice.")

    def _decompose(self, idx: int) -> tuple[int, int, int, int]:
        bits = self._BITS
        mask = self._MASK
        idx3 = idx & mask
        idx >>= bits
        idx2 = idx & mask
        idx >>= bits
        idx1 = idx & mask
        idx >>= bits
        return (idx, idx1, idx2, idx3)

    def _compose(self, key: tuple[int, int, int, int]) -> int:
        assert type(key) == tuple
        assert len(key) == 4
        c = self._CHUNKSIZE
        return ((key[0] * c + key[1]) * c + key[2]) * c + key[3]

    def _pool_get(self) -> list[Any]:
        if self._pool is not None and len(self._pool) > 0:
            obj = self._pool.pop()
            assert isinstance(obj, list)
            assert len(obj) == self._CHUNKSIZE
            return obj
        return self._pool_getnew()
    
    def _pool_reclaim(self, obj: list[Any]) -> None:
        assert isinstance(obj, list)
        assert len(obj) == self._CHUNKSIZE
        for idx in range(self._CHUNKSIZE):
            obj[idx] = None
        if self._pool is None:
            self._pool = [obj]
        else:
            self._pool.append(obj)

    def _pool_getnew(self) -> list[Any]:
        return [None] * self._CHUNKSIZE
