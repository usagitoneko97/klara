import unittest
from algebraic_identities import AlgIdent
from ssa import SsaVariable


class TestAlgIdent(unittest.TestCase):
    def assert_variable_list_equal(self, actual_list, expected_list):
        for i in range(len(actual_list)):
            self.assertEqual(str(actual_list[i]), str(expected_list[i]))

    # ---------- optimize alg identity----------

    def test_optimize_alg_ident_add(self):
        alg_ident = AlgIdent()
        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 
                                                            'Add',
                                                            SsaVariable(0))
        expected_list = [SsaVariable('a'), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Add', SsaVariable('b'))
        expected_list = [SsaVariable('a'), 'Add', SsaVariable('b')]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable(0), 'Add', SsaVariable('a'))
        expected_list = [SsaVariable('a'), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Add', SsaVariable('a'))
        expected_list = [2, 'Mult', SsaVariable('a')]
        self.assert_variable_list_equal([left, op, right], expected_list)

    def test_optimize_alg_ident_sub(self):
        alg_ident = AlgIdent()
        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Sub', SsaVariable(0))
        expected_list = [SsaVariable('a'), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Sub', SsaVariable('b'))
        expected_list = [SsaVariable('a'), 'Sub', SsaVariable('b')]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Sub', SsaVariable('a'))
        expected_list = [SsaVariable(0), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable(0), 'Sub', SsaVariable('a'))
        expected_list = [SsaVariable(0), 'Sub', SsaVariable('a')]
        self.assert_variable_list_equal([left, op, right], expected_list)

    def test_optimize_alg_ident_Mult(self):
        alg_ident = AlgIdent()
        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Mult', SsaVariable(0))
        expected_list = [SsaVariable(0), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable(0), 'Mult', SsaVariable('a'))
        expected_list = [SsaVariable(0), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Mult', SsaVariable(1))
        expected_list = [SsaVariable('a'), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable(1), 'Mult', SsaVariable('a'))
        expected_list = [SsaVariable('a'), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Mult', SsaVariable('b'))
        expected_list = [SsaVariable('a'), 'Mult', SsaVariable('b')]
        self.assert_variable_list_equal([left, op, right], expected_list)

    def test_optimize_alg_ident_Div(self):
        alg_ident = AlgIdent()
        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Div', SsaVariable('a'))
        expected_list = [SsaVariable(1), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable(0), 'Div', SsaVariable('a'))
        expected_list = [SsaVariable(0), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Div', SsaVariable(1))
        expected_list = [SsaVariable('a'), None, None]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable(1), 'Div', SsaVariable('a'))
        expected_list = [SsaVariable(1), 'Div', SsaVariable('a')]
        self.assert_variable_list_equal([left, op, right], expected_list)

        left, op, right = alg_ident.optimize_alg_identities(SsaVariable('a'), 'Div', SsaVariable('b'))
        expected_list = [SsaVariable('a'), 'Div', SsaVariable('b')]
        self.assert_variable_list_equal([left, op, right], expected_list)