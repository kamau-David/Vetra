import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_score, recall_score

LABELED_DIR = Path("data/labeled")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

FEATURE_COLUMNS = [
    "supply_log",
    "has_liquidity_pool",
]

OPTIONAL_LIVE_COLUMNS = [
    "owner_not_renounced",
]


def load_training_data():
    return pd.read_csv(LABELED_DIR / "training_data.csv")


def select_features(df):
    columns = FEATURE_COLUMNS.copy()
    for col in OPTIONAL_LIVE_COLUMNS:
        if col in df.columns and df[col].notna().any():
            columns.append(col)

    df = df.dropna(subset=["label"])
    X = df[columns].fillna(0)
    y = df["label"]
    return X, y, columns


def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=8, random_state=42, class_weight="balanced"
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["legit", "scam"]))
    print(f"Precision: {precision_score(y_test, y_pred):.3f}")
    print(f"Recall: {recall_score(y_test, y_pred):.3f}")

    return clf


def save_model(clf, columns):
    joblib.dump({"model": clf, "features": columns}, MODEL_DIR / "vetra_model.joblib")
    print(f"Saved model to {MODEL_DIR / 'vetra_model.joblib'}")


def main():
    df = load_training_data()
    X, y, columns = select_features(df)
    print(f"Training on {len(X)} rows using features: {columns}")

    clf = train_model(X, y)
    save_model(clf, columns)


if __name__ == "__main__":
    main()