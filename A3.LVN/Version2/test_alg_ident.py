import unittest
from algebraic_identities import AlgIdent


class TestAlgIdent(unittest.TestCase):
    # ---------- optimize alg identity----------

    def test_optimize_alg_ident_add(self):
        alg_ident = AlgIdent()
        left, op, right = alg_ident.optimize_alg_identities('a', 'Add', 0)
        expected_list = ['a', None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities('a', 'Add', 'b')
        expected_list = ['a', 'Add', 'b']
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(0, 'Add', 'a')
        expected_list = ['a', None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities('a', 'Add', 'a')
        expected_list = [2, 'Mult', 'a']
        self.assertListEqual([left, op, right], expected_list)

    def test_optimize_alg_ident_sub(self):
        alg_ident = AlgIdent()
        left, op, right = alg_ident.optimize_alg_identities('a', 'Sub', 0)
        expected_list = ['a', None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities('a', 'Sub', 'b')
        expected_list = ['a', 'Sub', 'b']
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities('a', 'Sub', 'a')
        expected_list = [0, None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(0, 'Sub', 'a')
        expected_list = [0, 'Sub', 'a']
        self.assertListEqual([left, op, right], expected_list)

    def test_optimize_alg_ident_Mult(self):
        alg_ident = AlgIdent()
        left, op, right = alg_ident.optimize_alg_identities('a', 'Mult', 0)
        expected_list = [0, None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(0, 'Mult', 'a')
        expected_list = [0, None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities('a', 'Mult', 1)
        expected_list = ['a', None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(1, 'Mult', 'a')
        expected_list = ['a', None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities('a', 'Mult', 'b')
        expected_list = ['a', 'Mult', 'b']
        self.assertListEqual([left, op, right], expected_list)

    def test_optimize_alg_ident_Div(self):
        alg_ident = AlgIdent()
        left, op, right = alg_ident.optimize_alg_identities('a', 'Div', 'a')
        expected_list = [1, None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(0, 'Div', 'a')
        expected_list = [0, None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities('a', 'Div', 1)
        expected_list = ['a', None, None]
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(1, 'Div', 'a')
        expected_list = [1, 'Div', 'a']
        self.assertListEqual([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities('a', 'Div', 'b')
        expected_list = ['a', 'Div', 'b']
        self.assertListEqual([left, op, right], expected_list)