# Loan Approval Prediction Model

# Streamlit App

🔗 **Streamlit Application:**

👉 https://loan-pred-approve-kpuqqryqvtwa7qhchzcpap.streamlit.app/

---

## 📃 Table of Contents

1. Project Overview
2. Files
3. Tools & Libraries
4. Keynotes
5. Future Improvements

--- 

## 📘 Project Overview

This project develops a machine learning model for predicting loan approval decisions based on applicant financial and demographic information. By applying data preprocessing, feature engineering, and multiple classification algorithms, the project aims to identify key factors influencing approval outcomes and improve predictive accuracy.

The project objectives are:

* Build and evaluate models for loan approval classification.
* Compare linear and ensemble machine learning methods.
* Provide insights into the most influential features driving loan approvals.

--- 

## 📂 Files

* `loan_prediction_data.csv` – Dataset containing applicant and loan information.
* `loan data.ipynb` – Jupyter Notebook containing preprocessing, model training, evaluation, and visualizations.
* `loan-app.py` – Streamlit dashboard/API: ensemble model training, hyperparameter tuning, class-imbalance handling, and SHAP explainability (also deployed live, see link above).

---

## ⚙️ Tools & Libraries

* Python
* Pandas / NumPy – Data preprocessing and handling categorical variables.
* Scikit-learn – Logistic Regression, Decision Trees, Random Forest, cross-validation, GridSearchCV/RandomizedSearchCV, evaluation metrics.
* XGBoost / LightGBM / CatBoost – Advanced gradient-boosting ensembles for higher accuracy.
* imbalanced-learn – SMOTE / SMOTEENN for class imbalance handling.
* SHAP – Explainable AI (XAI): global and per-applicant interpretation of loan decisions.
* Streamlit / Plotly – Interactive dashboard and visualizations.
* Matplotlib / Seaborn – Data exploration and visualization of results.

---

## 📝 Keynotes

* Applied data cleaning and preprocessing (handling missing values, encoding categorical features, scaling).
* Built and compared multiple models, including advanced ensemble methods:
  - Logistic Regression (baseline model)
  - Decision Tree Classifier
  - Random Forest Classifier
  - **XGBoost**, **LightGBM**, **CatBoost**

* Tuned and validated models with:
  - Stratified k-fold cross-validation
  - **GridSearchCV** and **RandomizedSearchCV** hyperparameter search, per-model search spaces

* Handled class imbalance in the target (`Loan_Status`) with **SMOTE** and **SMOTEENN** resampling, selectable from the app sidebar.

* Evaluated performance with metrics:
  - Accuracy
  - Precision, Recall, F1-score
  - ROC-AUC, ROC curve, threshold-sensitivity analysis
  - Confusion Matrix

* Added explainable AI (XAI) with **SHAP**:
  - Per-applicant waterfall plot and plain-language "why was this application approved/rejected" breakdown for every prediction
  - Global feature-impact summary plot across a sample of the test set

* Visualized model results and feature importance to interpret decision-making factors.

* Deployed as an interactive **Streamlit web application** (see link above) where users can enter applicant details and get a live prediction with full explainability.

---

## Images/Screenshots of the Work
![Streamlit Page 1](images/Streamlit_UI_1.png)
![Streamlit Page 2](images/Streamlit_UI_2.png)
![Streamlit Page 3](images/Streamlit_UI_3.png)
![Streamlit Page 4](images/Streamlit_UI_4.png)
![Streamlit Page 5](images/Streamlit_UI_5.png)
![Streamlit Page 6](images/Streamlit_UI_6.png)
![Streamlit Page 7](images/Streamlit_UI_7.png)
![Streamlit Page 8](images/Streamlit_UI_8.png)
![Streamlit Page 9](images/Streamlit_UI_9.png)

---

## 🚀 Future Improvements

* Persist trained models to disk (e.g. via `joblib`) so retraining isn't required on every session/deploy.
* Extend hyperparameter tuning with Bayesian optimization (e.g. Optuna) for a more efficient search than Grid/RandomizedSearchCV.
* Add LIME as a second, model-agnostic XAI method alongside SHAP for cross-checking explanations.
