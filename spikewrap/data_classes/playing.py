from dataclasses import dataclass


@dataclass
class A:
    one: int
    two: int

    def __post_init__(self):
        print("A")


@dataclass
class B(A):
    def __post_init__(self):
        super().__post_init__()
        print("B")


x = B(1, 2)
print(x)
