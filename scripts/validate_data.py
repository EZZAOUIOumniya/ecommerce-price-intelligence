import os
import pandas as pd

base_dir = os.path.dirname(os.path.dirname(__file__))
file_path = os.path.join(base_dir, "data", "cleaned_data.csv")

df = pd.read_csv(file_path)

print("Shape:", df.shape)
print("\nColumns:", df.columns)
print("\nMissing values:\n", df.isnull().sum())

assert df.shape[0] > 0, "Dataset vide !"

print("\nData validation OK ✅")