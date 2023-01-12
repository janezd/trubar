class PigManager:
    def __init__(self, n):
        if not 5 <= n <= 20:
            raise ValueError(
                f"Wrong number: {n} must be between 5 and 20.")
        self.n = n

    def walk(self):
        print(f"{self.n} little pigs went for a walk")
