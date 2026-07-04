def main():
    """
    Calculate the sum of two numbers entered by the user.
    
    Prompts the user to enter two numbers, calculates their sum,
    and displays the result.
    """
    num1 = float(input("Enter first number: "))
    num2 = float(input("Enter second number: "))

    sum = num1 + num2

    print(f"The sum of {num1} and {num2} is {sum}")


if __name__ == "__main__":
    main()
