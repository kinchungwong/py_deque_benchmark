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


from collections import deque
from collections.abc import Iterable
from typing import Union, Generic, TypeVar, Final, Optional, ForwardRef

_T = TypeVar("_T")
TrimList = ForwardRef("TrimList")

class TrimListWrapper(Generic[_T]):
    _upstream: TrimList
    _idx_map: Union[range, Iterable[int]]

    def __init__(self, upstream: TrimList, idx_map: Union[range, Iterable[int]]) -> None:
        assert isinstance(upstream, TrimList)
        assert isinstance(idx_map, (range, Iterable))
        self._upstream = upstream
        self._idx_map = idx_map
    
    def __getitem__(self, idx: int) -> _T:
        ###
        ### TODO Incomplete implementation of sliceable.
        ###
        return self._upstream[self._idx_map[idx]]


class TrimList(Generic[_T]):
    _data: Final[deque[_T]]
    _pop_count: int

    def __init__(self) -> None:
        self._data = deque[_T]()
        self._pop_count = 0

    def __len__(self) -> int:
        return self._pop_count + len(self._data)

    def indexrange(self) -> range:
        start = self._pop_count
        cur_len = len(self._data)
        return range(start, start + cur_len)

    def __getitem__(self, _slice: Union[int, slice, range, Iterable[int]]) -> Union[_T, TrimListWrapper[_T]]:
        ###
        ### TODO Incomplete implementation of sliceable.
        ###
        if isinstance(_slice, int):
            return self._data[_slice - self._pop_count]
        if isinstance(_slice, slice):
            _slice: range = range(_slice.start, _slice.stop, _slice.step)
        assert isinstance(_slice, Iterable)
        return TrimListWrapper(self, _slice)

    def append(self, value: _T) -> int:
        idx = len(self._data)
        self._data.append(value)
        return idx + self._pop_count

    def pop_left(self) -> Optional[_T]:
        if len(self._data) == 0:
            return None
        value = self._data.popleft()
        self._pop_count += 1
        return value

    def trim_before(self, idx: int) -> list[_T]:
        cur_len = len(self._data)
        target_len = max(0, cur_len + self._pop_count - idx)
        trim_count = max(0, cur_len - target_len)
        trimmed_values: list[_T] = []
        for _ in range(trim_count):
            trimmed_values.append(self._data.popleft())
        self._pop_count += trim_count
        return trimmed_values

      