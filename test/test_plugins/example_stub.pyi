class Base:
    attr: float = 1.0
    int_attr: int

class Example(Base):
    attr: str = "2"  # replaced with str
    def foo(self) -> float: ...
