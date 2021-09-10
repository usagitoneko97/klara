from klara.core.utilities import SubsetTree, TempAttr


class TestTempAttr:
    def test_temp_attr(self):
        class Temp:
            another = 1

        ins = Temp()
        with TempAttr(ins) as handler:
            handler.set_attr("temp", 2)
            handler.set_attr("another", 2)
            assert ins.temp == 2
            assert ins.another == 2
        assert not hasattr(ins, "temp")
        assert ins.another == 1


class TestSubsetTree:
    def build_sub_tree(self, lits):
        return SubsetTree.build_sub_tree((i, k) for i, k in enumerate(lits))

    def all_subset(self, tree):
        for children in tree.children:
            cs = list(c.key for c in children.all_children())
            yield [children.key] + cs

    def test_subset_tree(self):
        dictionary = {frozenset([1]): 1, frozenset([2]): 2, frozenset([3]): 3, frozenset([3, 4]): 34}
        st = self.build_sub_tree(dictionary.keys())
        res = list(self.all_subset(st))
        assert res == [[{3, 4}, {3}], [{1}], [{2}]]

    def test_subset_tree_1(self):
        dictionary = {frozenset([1]): 1, frozenset([1, 2]): 2, frozenset([1, 2, 3]): 3, frozenset([4]): 34}
        st = self.build_sub_tree(dictionary.keys())
        res = list(self.all_subset(st))
        assert res == [[{1, 2, 3}, {1, 2}, {1}], [{4}]]

    def test_subset_tree_2(self):
        dictionary = {frozenset([1, 2, 3]): 1, frozenset([2, 3]): 2, frozenset([1, 2]): 3, frozenset([3, 4]): 34}
        st = self.build_sub_tree(dictionary.keys())
        res = list(self.all_subset(st))
        assert res == [[{1, 2, 3}, {2, 3}, {1, 2}], [{3, 4}]]

    def test_subset_tree_3(self):
        dictionary = {
            frozenset([1, 2, 3]): 1,
            frozenset([1]): 2,
            frozenset([2]): 3,
            frozenset([3]): 3,
        }
        st = self.build_sub_tree(dictionary.keys())
        res = list(self.all_subset(st))
        assert res == [[{1, 2, 3}, {1}, {2}, {3}]]

    def test_subset_tree_multiple_values(self):
        dictionary = {
            frozenset([1, 2, 3]): 1,
            frozenset([1, 2, 4]): 2,
            frozenset([1, 2]): 3,
            frozenset([2, 4]): 3,
        }
        st = self.build_sub_tree(dictionary.keys())
        res = list(self.all_subset(st))
        assert res == [[{1, 2, 3}, {1, 2}], [{1, 2, 4}, {1, 2}, {2, 4}]]
