# Copyright 2024 Kin-Chung (Ryan) Wong
#
# This source file is made available under the MIT License. This license
# grant applies to the current source file only; it does not apply to
# any other file(s) that is/are found bundled within this repository.
#
# File(s) covered by this license grant: "demo_trimmable_list_benchmark.py"
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the “Software”), to deal in the Software 
# without restriction, including without limitation the rights to use, copy, modify, merge, 
# publish, distribute, sublicense, and/or sell copies of the Software, and to permit 
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE 
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.
#

from collections import defaultdict
import builtins
import random
import time
from typing import Final, Any, Protocol, runtime_checkable, Generic, TypeVar

from src.collections.trim_list.trim_list import TrimList
from src.collections.chunk_list.chunk_list import ChunkList

_T = TypeVar("_T")

@runtime_checkable
class TrimmableList(Protocol, Generic[_T]):
    def append(self, value: _T) -> int: ...
    def trim_before(self, idx: int) -> Any: ...
    def indexrange(self) -> range: ...
    def __getitem__(self, idx: int) -> _T: ...
    def __len__(self) -> int: ...


class ChunkListAdapter(TrimmableList):
    _impl: ChunkList[int]
    _trimmed: int

    def __init__(self) -> None:
        self._impl = ChunkList[int]()
        self._trimmed = 0

    def append(self, value: _T) -> int:
        self._impl.append(value)

    def trim_before(self, idx: int) -> Any:
        ### TODO Not yet implemented in ChunkList
        ###      Use dummy code here
        self._trimmed = max(self._trimmed, idx)
    
    def indexrange(self) -> range:
        kr = self._impl.keyrange()
        return range(self._trimmed, kr.stop)
    
    def __getitem__(self, idx: int) -> _T:
        if idx < self._trimmed:
            return None
        return self._impl.get(idx)
    
    def __len__(self) -> int:
        kr = self._impl.keyrange()
        return kr.stop


class TrimmableListBenchmarkBase:
    test_block_size: Final[int]
    blocks_to_add: Final[int]
    blocks_to_remove: Final[int]
    prob_add: Final[float]
    prob_remove: Final[float]
    test_data: Final[list[int]]

    def __init__(
        self,
        test_block_size: int,
        blocks_to_add: int,
        blocks_to_remove: int,
        prob_add: float,
        prob_remove: float,
    ) -> None:
        assert test_block_size > 0
        assert 0 < blocks_to_remove < blocks_to_add
        assert 0.01 <= prob_add <= 0.99
        assert 0.01 <= prob_remove <= 0.99
        self.test_block_size = test_block_size
        self.blocks_to_add = blocks_to_add
        self.blocks_to_remove = blocks_to_remove
        self.prob_add = prob_add
        self.prob_remove = prob_remove
        self._init_test_data()

    def _init_test_data(self) -> None:
        def test_data_func(idx: int) -> int:
            return builtins.hash((idx,))
        items_to_add = self.test_block_size * self.blocks_to_add
        self.test_data = [test_data_func(idx) for idx in range(items_to_add)]
    
    def randomized_populate(self, test_subject: TrimmableList) -> None:
        assert isinstance(test_subject, TrimmableList)
        assert len(test_subject) == 0
        _initial_indexrange = test_subject.indexrange()
        assert _initial_indexrange.start == 0
        assert _initial_indexrange.stop == 0
        pa = self.prob_add
        pr = self.prob_remove
        random_fn = random.random
        test_block_size = self.test_block_size
        items_to_add = test_block_size * self.blocks_to_add
        items_to_remove = test_block_size * self.blocks_to_remove
        test_data = self.test_data
        added_count = 0
        removed_count = 0
        can_add = (added_count < items_to_add)
        can_remove = (removed_count < items_to_remove)
        progress_update_count = 0
        while can_add or can_remove:
            has_changed = False
            if can_add and (random_fn() < pa):
                has_changed = True
                test_subject.append(test_data[added_count])
                added_count += 1
                can_add = (added_count < items_to_add)
            if can_remove and (removed_count < added_count) and (random_fn() < pr):
                has_changed = True
                removed_count += 1
                test_subject.trim_before(removed_count)
                can_remove = (removed_count < items_to_remove)
            ### for occasional progress printing
            if has_changed:
                progress_update_count += 1
                if ((progress_update_count % test_block_size) == 0):
                    print(f"... Added: {added_count}, Removed: {removed_count}")

    def sequential_verify(self, test_subject: TrimmableList) -> None:
        expect_items_added = self.test_block_size * self.blocks_to_add
        expect_items_removed = self.test_block_size * self.blocks_to_remove
        # expect_items_remain = expect_items_added - expect_items_removed
        test_data = self.test_data
        assert isinstance(test_subject, TrimmableList)
        assert len(test_subject) == expect_items_added
        _initial_indexrange = test_subject.indexrange()
        assert _initial_indexrange.start == expect_items_removed
        assert _initial_indexrange.stop == expect_items_added
        for idx in range(expect_items_removed, expect_items_added):
            expected_value = test_data[idx]
            actual_value = test_subject[idx]
            assert actual_value == expected_value

    def block_random_read(self, test_subject: TrimmableList) -> None:
        BN = self.test_block_size
        BA = self.blocks_to_add
        BR = self.blocks_to_remove
        assert isinstance(test_subject, TrimmableList)
        assert len(test_subject) == (BA * BN)
        _initial_indexrange = test_subject.indexrange()
        assert _initial_indexrange.start == (BR * BN)
        assert _initial_indexrange.stop == (BA * BN)
        timer_fn = time.perf_counter_ns
        round_count = (BA - BR) * 25
        raad_count_per_round = BN * 4
        round_target_list: list[int] = [0] * round_count
        round_timing_list: list[int] = [0] * round_count
        round_dummy_list: list[int] = [0] * round_count
        for round_idx in range(round_count):
            target_block = random.randint(BR, BA - 1)
            assert BR <= target_block < BA
            if (round_idx % 100) == 0:
                print(f"Randomized block test, round = {round_idx}, target_block = {target_block}")
            round_target_list[round_idx] = target_block
            read_range_start = target_block * BN
            read_range_stop = target_block * (BN + 1)
            read_idx_list = [
                random.randint(read_range_start, read_range_stop - 1)
                for _ in range(raad_count_per_round)
            ]
            dummy_sum = 0
            time_start = timer_fn()
            for idx in read_idx_list:
                dummy_sum += test_subject[idx]
            time_stop = timer_fn()
            assert time_start < time_stop 
            round_timing_list[round_idx] = time_stop - time_start
            round_dummy_list[round_idx] = dummy_sum
        block_timing_summary = [0] * BA
        block_opcount_summary = [0] * BA
        block_dummy_summary = [0] * BA
        for round_idx in range(round_count):
            target_block = round_target_list[round_idx]
            block_timing_summary[target_block] += round_timing_list[round_idx]
            block_opcount_summary[target_block] += raad_count_per_round
            block_dummy_summary[target_block] += round_dummy_list[round_idx]
        for target_block in range(BR, BA):
            read_range_start = target_block * BN
            read_range_stop = target_block * (BN + 1)
            total_ns = block_timing_summary[target_block]
            total_ops = block_opcount_summary[target_block]
            dummy_str = str(block_dummy_summary[target_block])
            dummy_str = dummy_str[:3] + "..." + dummy_str[-3:]
            ns_per_ops = total_ns / total_ops
            text = [
                f"Block [{target_block}], ",
                f"item index range ({read_range_start}, {read_range_stop}), ",
                f"avg_ns_per_read={ns_per_ops:.2f} = ",
                f"({total_ns} ns / {total_ops} ops), ",
                f"dummy = {dummy_str}"
            ]
            print("".join(text))


if __name__ == "__main__":

    for _ in range(3):
        ### to force VSCode terminal to flush. 
        ### It won't flush unless it's non-whitespace.
        print("_")

    print("====== BEGIN ======")

    benchmark_args = [
        ("test_block_size", 1000),
        ("blocks_to_add", 50),
        ("blocks_to_remove", 15),
        ("prob_add", 0.50),
        ("prob_remove", 0.15),
    ]

    for arg_name, arg_value in benchmark_args:
        print(f"Argument {arg_name} : {arg_value}")

    test_subject_list = [
        ("TrimList", lambda: TrimList[int]()),
        ("ChunkList", lambda: ChunkListAdapter()),
    ]

    for test_subject_name, test_subject_factory in test_subject_list:
        print(f"====== Begin Testing: {test_subject_name} ======")
        benchmark = TrimmableListBenchmarkBase(**dict(benchmark_args))

        test_subject = test_subject_factory()

        benchmark.randomized_populate(test_subject)
        benchmark.sequential_verify(test_subject)
        benchmark.block_random_read(test_subject)
        print(f"====== Finished Testing: {test_subject_name} ======")

    print("====== END ======")
