# ED_DDX_EVALUATION

## 설치
pip install streamlit pandas

## 실행
streamlit run app.py

## 기능 개요
본 툴은 **응급실 초진기록(ER Initial Record)** 과 LLM이 생성한 감별진단 결과(Base vs Applied)를 비교하고,  
의사가 직접 감별진단을 작성·평가할 수 있도록 설계된 Streamlit 기반 인터페이스입니다.  

---

## 화면 구성

### 1. 좌측 패널
- **Row Navigation**  
  - Selectbox로 행 선택  
  - `◀ Prev` / `Next ▶` 버튼으로 이전/다음 행 이동  
- **Core View**  
  - 기본적으로 Current History, Past History, 원본 초진기록 표시  
  - Model (Base / Applied) 감별진단 리스트는 숨겨져 있으며, 버튼 클릭 시 표시  
- **Optional Sections**  
  - 필요 시 추가 임상정보(ASSO_SX_SN, ASSO_DISEASE, ASSO_TREATMENT) 확인 가능  

---

### 2. 우측 패널 (Physician Evaluation)
의사는 다음 항목을 평가 및 입력할 수 있습니다:

- **Physician DDX 작성**  
  - 줄바꿈/쉼표로 구분하여 감별진단 리스트 직접 입력  

- **Likert 척도 평가**  
  1. Model (Base) DDX  
  2. Model (Applied) DDX  
  3. Current History + Past History (적절성 평가)  

- **Comment**  
  - 선택적으로 자유롭게 의견 입력 가능  

- **Save**  
  - 평가 내용은 **행 단위로 덮어쓰기** 저장됨  
  - 동일 행 중복 저장 시 기존 내용이 갱신됨  

- **Unreviewed 목록 + 점프**  
  - 평가되지 않은 행 목록을 표시  
  - 빠른 이동 버튼 제공  

- **CSV 다운로드**  
  - 중간 저장 가능  
  - 평가 내역(`file_name`, `reviewer`, Likert 점수, Physician DDX, comment 등)을 CSV로 다운로드  

---