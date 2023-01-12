from farm.pigs import PigManager

def main():
    print("This program serves no useful purpose.")
    ns = input("Enter a number between 5 and 20: ")
    try:
        n = int(ns)
    except ValueError:
        print(f"'{n}' is not a number.")
    else:
        farm = PigManager(n)
        farm.walk()

if __name__ == "__main__":
    main()
