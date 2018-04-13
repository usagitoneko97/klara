def get_something(x):
    if x == 1:
        return "something"
    return None

def main():
    x = get_something(0) or "another thing"
    print(x)


if __name__ == '__main__':
    main()
