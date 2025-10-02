import os
def main():
    print("ETL montado. ETL_BATCH_SIZE =", os.getenv("ETL_BATCH_SIZE", "10000"))
if __name__ == "__main__":
    main()
