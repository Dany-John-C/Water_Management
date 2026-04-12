import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

# 1. Load your exported data
# Replace with your actual CSV filename
df = pd.read_csv('exports/sensor_readings_20260412_190646.csv')

# 2. Define the scenario boundaries (based on your id segments)
def assign_label(row_id):
    if 110 <= row_id <= 186:
        return 1  # S2: Leak
    else:
        return 0  # S1 and S3: No Leak (Baseline or Fault)

df['label'] = df['id'].apply(assign_label)

# 3. Simulate Sliding Window Features (Simplified for the whole dataset)
# In a real pipeline, you'd group by window. Here we compute rolling deltas.# 3. Simulate Sliding Window Features
window_size = 5

df['delta_wl'] = df['water_level'].diff(periods=window_size).fillna(0)
df['avg_fr'] = df['flow_rate'].rolling(window=window_size).mean().fillna(0)
df['delta_sm'] = df['soil_moisture'].diff(periods=window_size).fillna(0)

# Safely handle the pump state column
if 'pump_state' in df.columns:
    pump_col = 'pump_state'
elif 'pm' in df.columns:
    pump_col = 'pm'
else:
    # Reconstruct based on your experimental protocol
    # S3 (IDs 234-273) is the only scenario where the pump was active
    df['inferred_pump_state'] = df['id'].apply(lambda x: 1 if 234 <= x <= 273 else 0)
    pump_col = 'inferred_pump_state'

df['pump_fraction'] = df[pump_col].rolling(window=window_size).mean().fillna(0)

# Drop early rows where rolling features aren't fully computed
features_df = df.iloc[window_size:].copy()

# 4. Prepare Features (X) and Target (y)
X = features_df[['delta_wl', 'avg_fr', 'delta_sm', 'pump_fraction']]
y = features_df['label']

# Split into train and test sets (stratified to ensure both classes are represented)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# 5. Train a lightweight Decision Tree (Max depth 3 to simulate edge constraints)
clf = DecisionTreeClassifier(max_depth=3, random_state=42)
clf.fit(X_train, y_train)

# 6. Evaluate
y_pred = clf.predict(X_test)
print("Decision Tree Baseline Results:")
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))
print("\nFeature Importances:")
for name, importance in zip(X.columns, clf.feature_importances_):
    print(f"{name}: {importance:.3f}")