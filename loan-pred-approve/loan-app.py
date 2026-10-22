# ============================================================================
# IMPORTS
# ============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

# Scikit-learn imports
from sklearn.model_selection import (
    train_test_split, StratifiedKFold, cross_val_score,
    GridSearchCV, RandomizedSearchCV
)
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)

# Advanced ensemble methods
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    st.warning("XGBoost not installed. Install with: pip install xgboost")

try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    st.warning("LightGBM not installed. Install with: pip install lightgbm")

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False

# Class imbalance handling
IMBALANCED_LEARN_AVAILABLE = False
IMBALANCED_LEARN_IMPORT_ERROR = None
try:
    from imblearn.over_sampling import SMOTE
    from imblearn.combine import SMOTEENN
    from imblearn.pipeline import Pipeline as ImbPipeline
    from collections import Counter
    IMBALANCED_LEARN_AVAILABLE = True
except ImportError as e:
    IMBALANCED_LEARN_IMPORT_ERROR = str(e)

# Explainable AI (XAI)
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

# ============================================================================
# DATA LOADING AND PREPROCESSING FUNCTIONS
# ============================================================================

def EDA(df):
    """
    Performs basic Exploratory Data Analysis (EDA) on a DataFrame.
    """
    print("===== Shape =====")
    print(df.shape)
    print("\n")

    print("===== Columns =====")
    print(df.columns)
    print("\n")

    numerical_cols = df.select_dtypes(include=[np.number]).columns
    print("===== Numerical Columns =====")
    print(numerical_cols)
    print("\n")

    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    print("===== Categorical Columns =====")
    print(categorical_cols)
    print("\n")

    print("===== Info =====")
    print(df.info())
    print("\n")

    print("===== Description =====")
    print(df.describe())
    print("\n")

    print("===== Head =====")
    print(df.head())
    print("\n")

    print("===== Null values =====")
    print(df.isnull().sum())
    print("\n")

    # Class distribution
    if 'Loan_Status' in df.columns:
        print("===== Loan Status Distribution =====")
        print(df['Loan_Status'].value_counts())
        print(f"Class Imbalance Ratio: {df['Loan_Status'].value_counts().min() / df['Loan_Status'].value_counts().max():.2f}")
        print("\n")


def fill_numerical_na(df, numerical_cols):
    """Fills missing values in numerical columns with median."""
    for col in numerical_cols:
        imputer = SimpleImputer(strategy='median')
        df[col] = imputer.fit_transform(df[[col]])
    return df


def fill_categorical_na(df, categorical_cols):
    """Fills missing values in categorical columns with mode."""
    for col in categorical_cols:
        imputer = SimpleImputer(strategy='most_frequent')
        df[col] = imputer.fit_transform(df[[col]]).ravel()
    return df


def plot_distribution(df, col_name):
    """Plots the distribution of a categorical column."""
    col_counts = df[col_name].value_counts()

    plt.figure(figsize=(8, 6))
    col_counts.plot(kind='bar')
    plt.title(f'Distribution of {col_name}')
    plt.xlabel(col_name)
    plt.ylabel('Frequency')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    fig = px.pie(values=col_counts.values, names=col_counts.index, title=f'{col_name} distribution')
    fig.show()


def create_boxplot(df, x_col, y_col, color_col, title):
    """Creates a box plot."""
    fig = px.box(df, x=x_col, y=y_col, color=color_col, title=title)
    fig.show()


def create_grouped_histogram(df, x_col, color_col, title):
    """Creates a grouped histogram."""
    fig = px.histogram(df, x=x_col, color=color_col, barmode='group', title=title)
    fig.show()


def remove_outliers(df, column_name):
    """Removes outliers from a DataFrame for a given column."""
    Q1 = df[column_name].quantile(0.25)
    Q3 = df[column_name].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df_out = df[(df[column_name] >= lower_bound) & (df[column_name] <= upper_bound)]
    return df_out


# ============================================================================
# MODEL TRAINING FUNCTIONS
# ============================================================================

def train_ensemble_models(X_train, y_train, X_test, y_test, use_smote=False):
    """
    Train multiple ensemble models and compare performance.

    Returns:
        dict: Dictionary containing trained models and their metrics
    """
    models = {}
    results = {}

    # Handle class imbalance if requested
    if use_smote and IMBALANCED_LEARN_AVAILABLE:
        print("Applying class imbalance handling...")
        print(f"Original distribution: {Counter(y_train)}")

        if st.session_state.get("imbalance_method") == "SMOTEENN":
            sampler = SMOTEENN(random_state=42)
            print("➡️ Using SMOTEENN")
        else:
            sampler = SMOTE(random_state=42)
            print("➡️ Using SMOTE")

        X_train_resampled, y_train_resampled = sampler.fit_resample(X_train, y_train)
        print(f"After resampling: {Counter(y_train_resampled)}")
        X_train_final, y_train_final = X_train_resampled, y_train_resampled
    else:
        X_train_final, y_train_final = X_train, y_train

    # XGBoost
    if XGBOOST_AVAILABLE:
        print("\n🔧 Training XGBoost...")
        xgb_model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric='logloss'
        )
        xgb_model.fit(X_train_final, y_train_final)
        xgb_pred = xgb_model.predict(X_test)
        xgb_proba = xgb_model.predict_proba(X_test)[:, 1]

        models['XGBoost'] = xgb_model
        results['XGBoost'] = {
            'predictions': xgb_pred,
            'probabilities': xgb_proba,
            'accuracy': accuracy_score(y_test, xgb_pred),
            'precision': precision_score(y_test, xgb_pred),
            'recall': recall_score(y_test, xgb_pred),
            'f1': f1_score(y_test, xgb_pred),
            'roc_auc': roc_auc_score(y_test, xgb_proba) if len(np.unique(y_test)) == 2 else None
        }
        print(f"  ✅ XGBoost - Accuracy: {results['XGBoost']['accuracy']:.4f}")

    # LightGBM
    if LIGHTGBM_AVAILABLE:
        print("\n🔧 Training LightGBM...")
        lgb_model = LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=-1
        )
        lgb_model.fit(X_train_final, y_train_final)
        lgb_pred = lgb_model.predict(X_test)
        lgb_proba = lgb_model.predict_proba(X_test)[:, 1]

        models['LightGBM'] = lgb_model
        results['LightGBM'] = {
            'predictions': lgb_pred,
            'probabilities': lgb_proba,
            'accuracy': accuracy_score(y_test, lgb_pred),
            'precision': precision_score(y_test, lgb_pred),
            'recall': recall_score(y_test, lgb_pred),
            'f1': f1_score(y_test, lgb_pred),
            'roc_auc': roc_auc_score(y_test, lgb_proba) if len(np.unique(y_test)) == 2 else None
        }
        print(f"  ✅ LightGBM - Accuracy: {results['LightGBM']['accuracy']:.4f}")

    # CatBoost
    if CATBOOST_AVAILABLE:
        print("\n🔧 Training CatBoost...")
        cat_model = CatBoostClassifier(
            iterations=100,
            depth=6,
            learning_rate=0.1,
            random_seed=42,
            verbose=False
        )
        cat_model.fit(X_train_final, y_train_final)
        cat_pred = cat_model.predict(X_test)
        cat_proba = cat_model.predict_proba(X_test)[:, 1]

        models['CatBoost'] = cat_model
        results['CatBoost'] = {
            'predictions': cat_pred,
            'probabilities': cat_proba,
            'accuracy': accuracy_score(y_test, cat_pred),
            'precision': precision_score(y_test, cat_pred),
            'recall': recall_score(y_test, cat_pred),
            'f1': f1_score(y_test, cat_pred),
            'roc_auc': roc_auc_score(y_test, cat_proba) if len(np.unique(y_test)) == 2 else None
        }
        print(f"  ✅CatBoost - Accuracy: {results['CatBoost']['accuracy']:.4f}")

    # Random Forest (baseline)
    print("\n🔧 Training Random Forest...")
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    rf_model.fit(X_train_final, y_train_final)
    rf_pred = rf_model.predict(X_test)
    rf_proba = rf_model.predict_proba(X_test)[:, 1]

    models['Random Forest'] = rf_model
    results['Random Forest'] = {
        'predictions': rf_pred,
        'probabilities': rf_proba,
        'accuracy': accuracy_score(y_test, rf_pred),
        'precision': precision_score(y_test, rf_pred),
        'recall': recall_score(y_test, rf_pred),
        'f1': f1_score(y_test, rf_pred),
        'roc_auc': roc_auc_score(y_test, rf_proba) if len(np.unique(y_test)) == 2 else None
    }
    print(f"  ✅ Random Forest - Accuracy: {results['Random Forest']['accuracy']:.4f}")

    return models, results


def hyperparameter_tuning(model_name, base_model, X_train, y_train, param_grid=None):
    """
    Perform hyperparameter tuning using GridSearchCV or RandomizedSearchCV.
    """
    if param_grid is None:
        # Default parameter grids
        if model_name == 'XGBoost' and XGBOOST_AVAILABLE:
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 6, 9],
                'learning_rate': [0.01, 0.1, 0.2]
            }
        elif model_name == 'LightGBM' and LIGHTGBM_AVAILABLE:
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 6, 9],
                'learning_rate': [0.01, 0.1, 0.2],
                'num_leaves': [31, 50, 100]
            }
        else:
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [3, 6, 9]
            }

    print(f"\n🔍 Tuning hyperparameters for {model_name}...")

    # Use RandomizedSearchCV for faster results
    grid_search = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=param_grid,
        n_iter=20,  # Number of random combinations
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        scoring='roc_auc',
        n_jobs=-1,
        random_state=42,
        verbose=1
    )

    grid_search.fit(X_train, y_train)

    print(f"  ✅ Best parameters: {grid_search.best_params_}")
    print(f"  ✅ Best CV score: {grid_search.best_score_:.4f}")

    return grid_search.best_estimator_


def cross_validate_model(model, X_train, y_train, cv_folds=5):
    """Perform cross-validation on a model."""
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    cv_scores = cross_val_score(
        model,
        X_train,
        y_train,
        cv=cv,
        scoring='roc_auc',
        n_jobs=-1
    )
    return cv_scores


def create_ensemble(models_dict, X_train, y_train):
    """Create voting ensemble from multiple models."""
    estimators = [(name, model) for name, model in models_dict.items()]

    # Voting Classifier
    voting_clf = VotingClassifier(
        estimators=estimators,
        voting='soft'
    )
    voting_clf.fit(X_train, y_train)

    return voting_clf


def get_best_model_name(results: dict) -> str:
    df = pd.DataFrame(results).T

    if "roc_auc" in df.columns and df["roc_auc"].notna().any():
        return df["roc_auc"].idxmax()
    else:
        return df["accuracy"].idxmax()

def get_feature_importance(model, feature_names):
    """
    Extract feature importance for tree-based and linear models.
    Returns a DataFrame or None if not supported.
    """
    if hasattr(model, "feature_importances_"):
        importance = model.feature_importances_
    elif hasattr(model, "coef_"):
        importance = np.abs(model.coef_[0])
    else:
        return None

    return (
        pd.DataFrame({
            "feature": feature_names,
            "importance": importance
        })
        .sort_values(by="importance", ascending=False)
        .reset_index(drop=True)
    )


def get_param_grid(model_name):
    """Hyperparameter search space for GridSearchCV / RandomizedSearchCV, per model."""
    grids = {
        "Random Forest": {
            "n_estimators": [50, 100, 200],
            "max_depth": [None, 5, 10, 20],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", "log2"],
        },
        "XGBoost": {
            "n_estimators": [50, 100, 200],
            "max_depth": [3, 6, 9],
            "learning_rate": [0.01, 0.05, 0.1],
            "subsample": [0.8, 1.0],
            "colsample_bytree": [0.8, 1.0],
        },
        "LightGBM": {
            "n_estimators": [50, 100, 200],
            "max_depth": [-1, 5, 10],
            "learning_rate": [0.01, 0.05, 0.1],
            "num_leaves": [31, 50, 100],
        },
        "CatBoost": {
            "iterations": [100, 200],
            "depth": [4, 6, 8],
            "learning_rate": [0.01, 0.05, 0.1],
        },
    }
    return grids.get(model_name)


# ============================================================================
# EXPLAINABLE AI (SHAP)
# ============================================================================

def compute_shap_values(model, X_background, X_explain, max_background=100):
    """
    Build a SHAP TreeExplainer (all models trained in this app are tree-based:
    XGBoost, LightGBM, CatBoost, Random Forest) and compute SHAP values for
    the rows in X_explain.
    """
    if not SHAP_AVAILABLE:
        raise RuntimeError("The 'shap' package is not installed.")

    background = X_background.sample(n=min(max_background, len(X_background)), random_state=42)
    explainer = shap.TreeExplainer(model, background)
    raw_values = explainer.shap_values(X_explain)

    # Normalize different explainer/model output shapes down to a single
    # (n_samples, n_features) array for the "approved" (positive) class.
    if isinstance(raw_values, list):
        shap_values = raw_values[1] if len(raw_values) > 1 else raw_values[0]
    else:
        shap_values = raw_values
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, 1]

    expected_value = explainer.expected_value
    if isinstance(expected_value, (list, np.ndarray)):
        expected_value = np.asarray(expected_value).reshape(-1)[-1]

    return {
        "shap_values": shap_values,
        "expected_value": float(expected_value),
        "X_explain": X_explain.reset_index(drop=True),
    }


def fig_shap_summary(shap_result, top_k=15):
    """Global feature-impact plot: which features push predictions toward approval/rejection."""
    plt.close("all")
    shap.summary_plot(
        shap_result["shap_values"],
        shap_result["X_explain"],
        max_display=top_k,
        show=False,
    )
    fig = plt.gcf()
    fig.tight_layout()
    return fig


def fig_shap_waterfall(shap_result, row_index: int = 0, max_display=12):
    """Local explanation for a single applicant's prediction."""
    X_explain = shap_result["X_explain"]
    explanation = shap.Explanation(
        values=shap_result["shap_values"][row_index],
        base_values=shap_result["expected_value"],
        data=X_explain.iloc[row_index].values,
        feature_names=list(X_explain.columns),
    )

    plt.close("all")
    shap.plots.waterfall(explanation, max_display=max_display, show=False)
    fig = plt.gcf()
    fig.tight_layout()
    return fig


def top_shap_contributors(shap_result, row_index: int = 0, top_k=5) -> str:
    """Plain-language summary of the top SHAP contributors for one applicant."""
    X_explain = shap_result["X_explain"]
    row = shap_result["shap_values"][row_index]
    feature_names = np.array(X_explain.columns)
    order = np.argsort(np.abs(row))[::-1][:top_k]

    lines = []
    for i in order:
        direction = "increased" if row[i] > 0 else "decreased"
        value = X_explain.iloc[row_index][feature_names[i]]
        lines.append(
            f"- **{feature_names[i]}** (value = `{value:.3f}`) {direction} the approval likelihood "
            f"(SHAP = `{row[i]:+.4f}`)"
        )
    return "\n".join(lines)


# ============================================================================
# STREAMLIT WEB APPLICATION
# ============================================================================

def create_streamlit_app():
    """Create Streamlit web application for loan prediction."""

    st.set_page_config(
        page_title="Loan Approval Predictor",
        page_icon="🏦",
        layout="wide"
    )

    st.title("🏦 Loan Approval Prediction System")
    st.markdown("Enter applicant information to predict loan approval")

    # ------------------------------------------------------------------
    # Session state initialization (IN-MEMORY ONLY)
    # ------------------------------------------------------------------
    if "trained_bundle" not in st.session_state:
        st.session_state.trained_bundle = None

    # Sidebar
    st.sidebar.header("Model Configuration")
    
    threshold = st.sidebar.slider(
        "Decision Threshold",
        min_value=0.1,
        max_value=1.0,
        value=st.session_state.get("threshold", 0.5),
        step=0.05,
        help="Probability required to approve a loan"
        )
    
    st.session_state.threshold = threshold

    st.sidebar.header("⚖️ Class Imbalance Handling")
    
    imbalance_method = st.sidebar.selectbox(
        "Imbalance Strategy",
        ["None", "SMOTE", "SMOTEENN"]
    )
    
    st.session_state.imbalance_method = imbalance_method
        
        
    st.sidebar.header("🤖 Model Selection")
        
    if st.session_state.trained_bundle is not None:
        model_names = list(st.session_state.trained_bundle["models"].keys())
        best_model_name = st.session_state.trained_bundle["best_model_name"]
        
        selected_model_name = st.sidebar.selectbox(
            "Choose model for prediction",
            model_names,
            index=model_names.index(best_model_name)
            )
            
    else:
        selected_model_name = None
        st.sidebar.info("Train the model to enable model selection.")
    

    # ======================
    # Model Evaluation 
    # ======================
    st.sidebar.header("🧪 Model Evaluation")
    
    cv_folds = st.sidebar.slider(
        "CV folds",
        min_value=3,
        max_value=10,
        value=5
        )

    evaluation_allowed = st.session_state.trained_bundle is not None

    run_cv = st.sidebar.checkbox("Run Cross-Validation", disabled = not evaluation_allowed)
    run_grid = st.sidebar.checkbox("Run GridSearchCV", disabled = not evaluation_allowed)
    run_random = st.sidebar.checkbox("Run RandomizedSearchCV", disabled = not evaluation_allowed)

    if st.session_state.trained_bundle is None:
        st.sidebar.warning("Train the model first to enable evaluation tools.")
        run_cv = False
        run_grid = False
        run_random = False

    if run_cv:
        bundle = st.session_state.trained_bundle
        best_model = bundle["models"][selected_model_name]

        X_train = bundle["X_train"]
        y_train = bundle["y_train"]

        with st.spinner("Running cross-validation..."):
            cv = StratifiedKFold(
                n_splits=cv_folds,
                shuffle=True,
                random_state=42
            )

            scores = cross_val_score(
                best_model,
                X_train,
                y_train,
                cv=cv,
                scoring="roc_auc",
                n_jobs=-1
            )
            
            st.subheader("📊 Cross-Validation Results")
            st.write("ROC-AUC scores:", scores)
            st.metric("Mean ROC-AUC", scores.mean())
            
    if run_grid:
        bundle = st.session_state.trained_bundle
        grid_model = bundle["models"][selected_model_name]
        X_train_search = bundle["X_train"]
        y_train_search = bundle["y_train"]
        param_grid = get_param_grid(selected_model_name)

        if param_grid is None:
            st.warning(f"GridSearchCV param grid not defined for {selected_model_name}.")
        else:
            with st.spinner("Running GridSearchCV..."):
                grid = GridSearchCV(
                    grid_model,
                    param_grid=param_grid,
                    scoring="roc_auc",
                    cv=cv_folds,
                    n_jobs=-1
                )
                grid.fit(X_train_search, y_train_search)

                st.subheader("🔍 GridSearchCV Results")
                st.write("Best Params:", grid.best_params_)
                st.metric("Best ROC-AUC", grid.best_score_)

                # Update model in session state
                st.session_state.trained_bundle["models"][selected_model_name] = grid.best_estimator_

    if run_random:
        bundle = st.session_state.trained_bundle
        rand_model = bundle["models"][selected_model_name]
        X_train_search = bundle["X_train"]
        y_train_search = bundle["y_train"]
        param_dist = get_param_grid(selected_model_name)

        if param_dist is None:
            st.warning(f"RandomizedSearchCV not supported for {selected_model_name}.")
        else:
            with st.spinner("Running RandomizedSearchCV..."):
                rand = RandomizedSearchCV(
                    rand_model,
                    param_distributions=param_dist,
                    n_iter=10,
                    cv=cv_folds,
                    scoring="roc_auc",
                    random_state=42,
                    n_jobs=-1
                )

                rand.fit(X_train_search, y_train_search)

                st.subheader("🎲 RandomizedSearchCV Results")
                st.write("Best Params:", rand.best_params_)
                st.metric("Best ROC-AUC", rand.best_score_)

                # Update model in session state
                st.session_state.trained_bundle["models"][selected_model_name] = rand.best_estimator_

    # ------------------------------------------------------------------
    # Train model button
    # ------------------------------------------------------------------
    if st.sidebar.button("🧠 Train Model (In Memory)"):
        with st.spinner("Training model... please wait"):
            (
                models,
                results,
                best_model,
                scaler,
                encoders,
                target_encoder,
                X_test,
                y_test,
                best_model_name,
                X_train,
                y_train,
            ) = train_cached()

            best_model_name = max(
                results,
                key=lambda k: results[k]["roc_auc"]
                if results[k]["roc_auc"] is not None
                else results[k]["accuracy"]
            )

            # Store trained objects in memory
            st.session_state.trained_bundle = {
                "models": models,                     # <-- ALL models
                "best_model_name": best_model_name,   # <-- Best model name
                "results": results,
                "scaler": scaler,
                "encoders": encoders,
                "target_encoder": target_encoder,
                "X_test": X_test,
                "y_test": y_test,
                "X_train": X_train,
                "y_train": y_train,
            }


        st.sidebar.success("✅ Model trained successfully (not saved)")

    # ------------------------------------------------------------------
    # Input form
    # ------------------------------------------------------------------
    st.header("📝 Applicant Information")

    col1, col2 = st.columns(2)

    with col1:
        gender = st.selectbox("Gender", ["Male", "Female"])
        married = st.selectbox("Married", ["Yes", "No"])
        dependents = st.selectbox("Dependents", ["0", "1", "2", "3+"])
        education = st.selectbox("Education", ["Graduate", "Not Graduate"])
        self_employed = st.selectbox("Self Employed", ["Yes", "No"])

    with col2:
        applicant_income = st.number_input("Applicant Income ($)", 0, 1_000_000, 5000)
        coapplicant_income = st.number_input("Coapplicant Income ($)", 0, 1_000_000, 0)
        loan_amount = st.number_input("Loan Amount ($)", 0, 1_000_000, 100000)
        loan_term = st.number_input("Loan Amount Term (months)", 12, 480, 360)
        credit_history = st.selectbox("Credit History", [1.0, 0.0])
        property_area = st.selectbox("Property Area", ["Urban", "Semiurban", "Rural"])

    # ------------------------------------------------------------------
    # Prediction logic
    # ------------------------------------------------------------------
    if st.button("🔮 Predict Loan Approval", type="primary"):
        importance_df = None

        if st.session_state.trained_bundle is None:
            st.info("👈 Train the model from the sidebar to continue.")
            return

        bundle = st.session_state.trained_bundle
        
        if selected_model_name is None:
            st.warning("Please train the model first.")
            return
            
        best_model = bundle["models"][selected_model_name]

        scaler = bundle["scaler"]
        encoders = bundle["encoders"]

        # Prepare input data
        input_data = pd.DataFrame({
            'Gender': [gender],
            'Married': [married],
            'Dependents': [dependents],
            'Education': [education],
            'Self_Employed': [self_employed],
            'ApplicantIncome': [applicant_income],
            'CoapplicantIncome': [coapplicant_income],
            'LoanAmount': [loan_amount],
            'Loan_Amount_Term': [loan_term],
            'Credit_History': [credit_history],
            'Property_Area': [property_area]
        })

        # Encode categorical variables
        categorical_cols = [
            'Gender', 'Married', 'Dependents',
            'Education', 'Self_Employed', 'Property_Area'
        ]
        for col in categorical_cols:
            if col in encoders:
                try:
                    input_data[col] = encoders[col].transform(input_data[col])
                except ValueError:
                    st.error(f"Unrecognized category for {col}. Please retrain the model.")
                    return

        # Scale numerical features
        numerical_cols = [
            'ApplicantIncome', 'CoapplicantIncome',
            'LoanAmount', 'Loan_Amount_Term', 'Credit_History'
        ]
        input_data[numerical_cols] = scaler.transform(input_data[numerical_cols])

        # Predict probability
       
        probability = best_model.predict_proba(input_data)[0]

        # Apply decision threshold
        threshold = st.session_state.threshold
        prediction = int(probability[1] >= threshold)

        # Display results
        st.header("📊 Prediction Result")

        if prediction == 1:
            st.success("✅ **LOAN APPROVED**")
            st.info(f"Approval Probability: {probability[1] * 100:.2f}%")

        else:
            st.error("❌ **LOAN REJECTED**")
            st.info(f"Rejection Probability: {probability[0] * 100:.2f}%")


        st.header("🏆 Model Comparison")
        
        results = st.session_state.trained_bundle["results"]
        best_model_name = st.session_state.trained_bundle["best_model_name"]
        
        comparison_df = pd.DataFrame(results).T[
        ["accuracy", "precision", "recall", "f1", "roc_auc"]
        ].round(3)

        st.dataframe(comparison_df, use_container_width=True)
        
        best_model_name = get_best_model_name(results)
        
        comparison_df["Best"] = comparison_df.index.map(
            lambda x: "⭐" if x == best_model_name else ""
        )
        
        st.dataframe(comparison_df.style)
        
        st.success(f"⭐ Best Model: {best_model_name}")

        
        # Feature importance
        importance_df = get_feature_importance(
            best_model,
            st.session_state.trained_bundle["X_test"].columns.tolist()
            )


        if importance_df is not None:
            st.header("🔍 Feature Importance")
            fig = px.bar(
                importance_df.head(10),
                x="importance",
                y="feature",
                orientation="h",
                title="Top 10 Feature Importances"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Explainable AI (SHAP): explain this specific applicant's prediction
        st.header("🧠 Why This Decision? (SHAP Explainability)")
        if SHAP_AVAILABLE:
            try:
                shap_result = compute_shap_values(best_model, bundle["X_train"], input_data)
                contributors_text = top_shap_contributors(shap_result, row_index=0)
                st.markdown(f"**Top factors behind this applicant's prediction:**\n\n{contributors_text}")

                waterfall_fig = fig_shap_waterfall(shap_result, row_index=0)
                st.pyplot(waterfall_fig)

                with st.expander("📊 Global feature impact (SHAP summary across the test set)"):
                    X_test_bundle = bundle["X_test"]
                    X_test_sample = X_test_bundle.sample(
                        n=min(200, len(X_test_bundle)), random_state=42
                    )
                    global_shap_result = compute_shap_values(best_model, bundle["X_train"], X_test_sample)
                    summary_fig = fig_shap_summary(global_shap_result)
                    st.pyplot(summary_fig)
            except Exception as e:
                st.warning(f"⚠️ Could not generate SHAP explanation: {e}")
        else:
            st.info("Install the `shap` package (see requirements.txt) to see feature-level explanations for this prediction.")

        st.header("📐 Model Performance (Test Set)")
        
        model_metrics = bundle["results"][selected_model_name]
        
        with st.container():
            col1, col2, col3, col4, col5 = st.columns(5)
            
            col1.metric("Accuracy", f"{model_metrics['accuracy']:.3f}")
            col2.metric("Precision", f"{model_metrics['precision']:.3f}")
            col3.metric("Recall", f"{model_metrics['recall']:.3f}")
            col4.metric("F1 Score", f"{model_metrics['f1']:.3f}")
            col5.metric("ROC-AUC", f"{model_metrics['roc_auc']:.3f}")


        
        # Confusion Matrix
        st.header("🧮 Confusion Matrix (Test Set)")
         
        X_test = st.session_state.trained_bundle["X_test"]
        y_test = st.session_state.trained_bundle["y_test"]

        # Get test-set probabilities
        y_test_proba = best_model.predict_proba(X_test)[:, 1]

        # Apply threshold
        y_test_pred_threshold = (y_test_proba >= threshold).astype(int)

        # Compute confusion matrix
        cm = confusion_matrix(y_test, y_test_pred_threshold)
        
        tn, fp, fn, tp = cm.ravel()
        
        st.caption(
            f"True Positive Rate (Recall): {tp / (tp + fn):.2f} | "
            f"False Positive Rate: {fp / (fp + tn):.2f}"
        )

        cm_fig = px.imshow(
            cm,
            text_auto=True,
            color_continuous_scale="Blues",
            labels=dict(x="Predicted", y="Actual"),
            x=["Rejected", "Approved"],
            y=["Rejected", "Approved"],
            title=f"Confusion Matrix (Threshold = {threshold:.2f})"
        )

        st.plotly_chart(cm_fig, use_container_width=True)

        
        # Threshold Sensitivity Analysis
        st.header("📉 Threshold Sensitivity Analysis")

        thresholds = np.linspace(0.01, 0.99, 99)

        precisions = []
        recalls = []
        f1s = []

        for t in thresholds:
            preds = (y_test_proba >= t).astype(int)
            precisions.append(precision_score(y_test, preds, zero_division=0))
            recalls.append(recall_score(y_test, preds))
            f1s.append(f1_score(y_test, preds))

        threshold_df = pd.DataFrame({
            "Threshold": thresholds,
            "Precision": precisions,
            "Recall": recalls,
            "F1 Score": f1s
        })

        threshold_fig = px.line(
            threshold_df,
            x="Threshold",
            y=["Precision", "Recall", "F1 Score"],
            title="Precision / Recall / F1 vs Decision Threshold"
        )
        
        threshold_fig.add_vline(
            x=threshold,
            line_dash="dash",
            line_color="black",
            annotation_text=f"Selected Threshold = {threshold:.2f}"
        )

        st.plotly_chart(threshold_fig, use_container_width=True)


        # ROC Curve
        st.header("📈 ROC Curve (Test Set)")

        fpr, tpr, _ = roc_curve(y_test, y_test_proba)

        roc_fig = px.line(
            x=fpr,
            y=tpr,
            title="ROC Curve",
            labels={"x": "False Positive Rate", "y": "True Positive Rate"}
        )


        roc_fig.add_annotation(
            x=0.6,
            y=0.1,
            text=f"AUC = {model_metrics['roc_auc']:.3f}",
            showarrow=False
        )

        roc_fig.add_shape(
            type="line",
            x0=0, y0=0,
            x1=1, y1=1,
            line=dict(dash="dash")
        )

        st.plotly_chart(roc_fig, use_container_width=True)


        # Approval Probability Gauge
        st.header("🎯 Approval Probability Gauge")

        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=probability[1] * 100,
            title={"text": "Approval Probability (%)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "green"},
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "value": threshold * 100
                },
                "steps": [
                    {"range": [0, 40], "color": "#ffcccc"},
                    {"range": [40, 70], "color": "#fff3cd"},
                    {"range": [70, 100], "color": "#d4edda"}
                ]
            }
        ))


        st.plotly_chart(gauge_fig, use_container_width=True)


    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.header("ℹ️ About")
    st.sidebar.info("""
This application uses advanced machine learning models
to predict loan approval decisions.

**Features:**
    - XGBoost, LightGBM, CatBoost, RandomForest
    - SMOTE, SMOTENN for class imbalance
    - GridSearchCV / RandomizedSearchCV
    - ROC, PR curves
    - Gauge visualization
    - Feature importance bar charts
    - Threshold tuning
    - Cross-validation
    - Stable Streamlit deployment
    """)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

@st.cache_resource
def train_cached():
    return main(debug = False)

def main(debug = False):
    """Main execution function."""

    print("=" * 80)
    print("ENHANCED LOAN APPROVAL PREDICTION SYSTEM")
    print("=" * 80)

    # Load data
    # Try multiple possible file paths
    possible_paths = [
        "/users/marco/Downloads/loan_prediction_data.csv",  # Standard path
        "/users/marco/Downloads/oan_prediction_data.csv",   # User specified path (possible typo)
        "loan_prediction_data.csv",  # Current directory
        "oan_prediction_data.csv"    # Current directory (possible typo)
    ]

    loan_data = None
    for file_path in possible_paths:
        try:
            print(f"\n📂 Attempting to load data from: {file_path}")
            loan_data = pd.read_csv(file_path)
            print(f"✅ Successfully loaded data from: {file_path}")
            break
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"⚠️ Error loading {file_path}: {e}")
            continue

    if loan_data is None:
        raise FileNotFoundError(
            "Could not find loan data file. Please check the file path. "
            "Tried: " + ", ".join(possible_paths)
        )

    # EDA
    print("\n" + "=" * 80)
    print("EXPLORATORY DATA ANALYSIS")
    print("=" * 80)
    if debug:
        EDA(loan_data)

    # Data preprocessing
    print("\n" + "=" * 80)
    print("DATA PREPROCESSING")
    print("=" * 80)

    # Fill missing values
    fill_numerical_na(loan_data, ['ApplicantIncome', 'CoapplicantIncome', 'LoanAmount', 'Loan_Amount_Term', 'Credit_History'])
    fill_categorical_na(loan_data, ['Loan_ID', 'Gender', 'Married', 'Dependents', 'Education', 'Self_Employed', 'Property_Area', 'Loan_Status'])

    print("\nMissing values after preprocessing:")
    print(loan_data.isnull().sum())

    # Drop Loan_ID (not Loan_Status - that's the target!)
    if 'Loan_ID' in loan_data.columns:
        loan_data = loan_data.drop('Loan_ID', axis=1)

    # Encode categorical variables
    print("\n🔧 Encoding categorical variables...")
    encoders = {}  # Store encoders for each column
    categorical_cols = ['Gender', 'Married', 'Dependents', 'Education', 'Self_Employed', 'Property_Area']
    for col in categorical_cols:
        if col in loan_data.columns:
            encoder = LabelEncoder()
            loan_data[col] = encoder.fit_transform(loan_data[col])
            encoders[col] = encoder

    # Encode target variable
    target_encoder = LabelEncoder()
    if 'Loan_Status' in loan_data.columns:
        loan_data['Loan_Status'] = target_encoder.fit_transform(loan_data['Loan_Status'])

    # Prepare features and target
    X = loan_data.drop('Loan_Status', axis=1)
    y = loan_data['Loan_Status']

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\n📊 Train set: {X_train.shape[0]} samples")
    print(f"📊 Test set: {X_test.shape[0]} samples")

    # Scale numerical features
    print("\n🔧 Scaling numerical features...")
    scaler = StandardScaler()
    numerical_cols = ['ApplicantIncome', 'CoapplicantIncome', 'LoanAmount', 'Loan_Amount_Term', 'Credit_History']
    X_train[numerical_cols] = scaler.fit_transform(X_train[numerical_cols])
    X_test[numerical_cols] = scaler.transform(X_test[numerical_cols])

    # Train ensemble models
    print("\n" + "=" * 80)
    print("TRAINING ENSEMBLE MODELS")
    print("=" * 80)

    # Train without SMOTE first
    use_smote = st.session_state.imbalance_method in ["SMOTE", "SMOTEENN"]

    models, results = train_ensemble_models(
        X_train,
        y_train,
        X_test,
        y_test,
        use_smote=use_smote
    )


    # Train with SMOTE
    if IMBALANCED_LEARN_AVAILABLE:
        print("\n" + "=" * 80)
        print("TRAINING WITH SMOTE (Class Imbalance Handling)")
        print("=" * 80)
        models_smote, results_smote = train_ensemble_models(X_train, y_train, X_test, y_test, use_smote=True)

    # Compare results
    print("\n" + "=" * 80)
    print("MODEL COMPARISON")
    print("=" * 80)

    comparison_df = pd.DataFrame(results).T
    print("\n📊 Model Performance Comparison:")
    print(comparison_df[['accuracy', 'precision', 'recall', 'f1', 'roc_auc']])

    # Select best model
    best_model_name = comparison_df['roc_auc'].idxmax() if 'roc_auc' in comparison_df.columns else comparison_df['accuracy'].idxmax()
    best_model = models[best_model_name]

    print(f"\n🏆 Best Model: {best_model_name}")
    print(f"   Accuracy: {results[best_model_name]['accuracy']:.4f}")
    print(f"   ROC-AUC: {results[best_model_name].get('roc_auc', 'N/A')}")

    # Cross-validation
    print("\n" + "=" * 80)
    print("CROSS-VALIDATION")
    print("=" * 80)
    cv_scores = cross_validate_model(best_model, X_train, y_train, cv_folds=5)
    print(f"\n📊 Cross-Validation Scores: {cv_scores}")
    print(f"   Mean: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

    # Feature importance
    print("\n" + "=" * 80)
    print("FEATURE IMPORTANCE")
    print("=" * 80)
    importance_df = get_feature_importance(best_model, X_train.columns.tolist())
    if importance_df is not None:
        print("\n📊 Top 10 Most Important Features:")
        print(importance_df.head(10))

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE!")
    print("=" * 80)
    print("\n🚀 To launch the Streamlit app, run:")
    print("   streamlit run loan_approval_enhanced.py")
    return ( 
        models, 
        results, 
        best_model, 
        scaler, 
        encoders, 
        target_encoder, 
        X_test, 
        y_test, 
        best_model_name,
        X_train,
        y_train
    )

# ============================================================================
# STREAMLIT APP ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run Streamlit app
    create_streamlit_app()