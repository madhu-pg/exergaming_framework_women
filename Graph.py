import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
data = pd.read_csv("exergame_results.csv", encoding="cp1252")


# Plot Exercise vs Score
plt.figure()
plt.bar(data["Exercise_Type"], data["Score"])
plt.xlabel("Exercise Type")
plt.ylabel("Score")
plt.title("Performance Across Exergames")
plt.xticks(rotation=45)
plt.show()
