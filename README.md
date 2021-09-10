# Klara

Klara is a static analysis tools to automatic generate test case, based
on SMT (z3) solver, with a powerful ast level inference system. Klara
will take python file as input and generate corresponding test file in
pytest format, that attempt to cover all return values. For example,
following function in file `test.py`

``` python
def triangle(x: int, y: int, z: int) -> str:
    if x == y == z:
        return "Equilateral triangle"
    elif x == y or y == z or x == z:
        return "Isosceles triangle"
    else:
        return "Scalene triangle"
```

will generate

``` python
import test
def test_triangle_0():
    assert test.triangle(0, 0, 0) == 'Equilateral triangle'
    assert test.triangle(0, 0, 1) == 'Isosceles triangle'
    assert test.triangle(2, 0, 1) == 'Scalene triangle'
```

See the Klara\'s documentation at <https://klara-py.readthedocs.io>

## Installing

Klara can be installed via `pip` tool by using:

    pip install klara

## Usage

We can invoke `klara` on any python source file, and it will generate a
corresponding pytest test file.

``` shell
$ cat source.py
def foo(x: int, y: int, z: str):
    if x + y > 2:
        return x + y + 12
    elif x < y:
        return x + y
    elif (z + "me") == "some":
        return z + "thing"
    else:
        return x - y

$ klara source.py
$ cat test_source.py
import contract_test


def test_foo_0():
    assert contract_test.foo(0, 3, \'\') == 15
    assert contract_test.foo(0, 1, \'\') == 1
    assert contract_test.foo(0, 0, \'so\') == \'sothing\'
    assert contract_test.foo(0, 0, \'\') == 0
```

Consult the [quick start](quick_start.html) manual for more examples and
guidance. To use it as a static analysis library, go to
[Inference](inference.html).

## Why Klara?

Klara works on ast level and it doesn\'t execute user code in any way,
which is a very important difference compared to similar tool like
[Crosshair](https://github.com/pschanely/CrossHair) and
[Pynguin](https://github.com/se2p/pynguin) that utilize concolic
symbolic execution that required user code execution that might cause
side effects. Klara work on ast level, combine with data flow analysis
that utilize CFG, SSA, use-def chain, SMT solver etc\... to build a
powerful python inference system that leverages Z3-solver for
constraints solving and path feasibility check. Because of this, Klara
is able to operate on both python2/3 source code with the help of
[typed_ast](https://github.com/python/typed_ast). To specify the source
code is in python 2, pass in `-py 2` argument. It\'s python 3 by
default.

Klara can also be used as a static analysis tool, allow user to define
custom rule to identify programming bugs, error or enforcing coding
standard. With SMT solver support, analysis will be more accurate and
greatly reduce false-positive case. For example

``` python
from klara import parse
tree = parse("""
    if cond():
        x = 1
        y = 10
    else:
        x = 2
        y = 20
    s = (x + y) + (x + y)
""")
variable_s = tree.body[-1].targets[0]
print(list(variable_s.infer()))
```

Will print out:

    [6, 12]

The inference system architecture and api is largely inspired by
[Astroid](https://github.com/PyCQA/astroid), a static inference library
used by [Pylint](https://github.com/PyCQA/pylint).

Klara utilize the inference system to generate test case, in other
words, it **generate test case for all possible return values of the
function**, instead of generate test case for all control path of the
function.

To illustrate the point, consider the function below, with [divide by
zero]{.title-ref} vulnerabilities at line 3

``` python
def foo(v1: int, v2: float):
if v1 > 10000:
s = v1 / 0  # unused statement
if v1 > v2:
s = v1
else:
s = v2
return s
```

Klara will generate test inputs below

``` python
import contract_test
def test_foo_0():
    assert contract_test.foo(0, -1.0) == 0
    assert contract_test.foo(0, 0.0) == 0.0
```

It doesn\'t generate input `v1 > 10000`, so the test case would not be
able to find out the exceptions. This is because the [s]{.title-ref} at
line 3 is unused in the return value.

::: note
::: title
Note
:::

If we modify the second if statement to [elif]{.title-ref}, which we\'ll
be able to return the [s]{.title-ref} at line 3, klara will generate
test inputs that cover `v1 > 10000` case.
:::

This is an important distinction with other automatic test case
generation available now, because by only generate test case for return
values, we can generate a minimal test case, and it\'s easier to
customize how do Klara cover the function.

For example, say we are composing a complex system

``` python
    def main(number: int, cm: int, dc: int, wn: int):
        mc = 0
        if wn > 2:
            if number > 2 and number > 2 or number > 2:
                if number > 0:
                    if wn > 2 or wn > 2:
                        mc = 2
                    else:
                        mc = 5
                else:
                    mc = 100
        else:
            mc = 1
        nnn = number * cm
        if cm <= 4:
            num_incr = 4
        else:
            num_incr = cm
        n_num_incr = nnn / num_incr
        nnn_left = dc * num_incr * (n_num_incr / 2 + n_num_incr % 2)
        nnn_right = nnn - nnn_left
        is_flag = nnn_right
        if is_flag:
            cell = Component(nnn_right, options=[mc])
        else:
            cell = Component(nnn_right)
        return cell
```

It isn\'t immediately clear to us how many possible return values there
are. But we can utilize Klara to generate inputs instantly, below is the
generated test

``` python
import contract_test
def test_main_0():
    assert contract_test.main(2, 4, 1, 3) is not None
    assert contract_test.main(2, 4, -1, 6) is not None
    assert contract_test.main(2, 4, 1, 4) is not None
    assert contract_test.main(-2, 4, 3, 4) is not None
    assert contract_test.main(-1, -1, -1, 2) is not None
    assert contract_test.main(0, 0, 0, 3) is not None
    assert contract_test.main(0, 0, 0, 6) is not None
    assert contract_test.main(0, 0, 0, 4) is not None
    assert contract_test.main(-2, 0, 0, 4) is not None
    assert contract_test.main(0, 0, 0, 0) is not None
```

Above generated 10 total results, which is product of
[pc_right]{.title-ref} which have 2 possibilities and [mc]{.title-ref}
which have 5 possibilities.

Suppose that 10 tests input is too much, and we have determine that the
[options]{.title-ref} argument to `Component` is redundant to test, we
can use Klara\'s custom plugin to selectively determine which part to
ignore in test generation. Go to [customize coverage
strategy](customize_coverage_strategy.html) for more information.

After we have setup the plugin, Klara will generate following test

``` python
import contract_test
def test_main_0():
    assert contract_test.main(1, 3, 0, 0) == 3.0
    assert contract_test.main(0, 0, 0, 0) == 0.0
```

Which is only 2 combinations of `pc_right`

Klara will also provide extension to specify how to infer unknown ast
node or user defined type to make Klara \'smarter\'. It\'s described in
[extending](extending.html), [extending user
type](extending_user_type.html) and [customize coverage
strategy](customize_coverage_strategy.html).

## Contributing

We use [Poetry](https://python-poetry.org/docs/) to manage dependencies.
After poetry is installed, run:

    $ poetry shell
    $ poetry install

To run the test case, do:

    $ poetry run pytest test

## License

This project is licensed under the terms of the GNU Lesser General
Public License.
