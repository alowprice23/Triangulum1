def helper():
    # BUG: off-by-one in a loop
    numbers = []
    for i in range(1, 6):
        numbers.append(i)
    return numbers
