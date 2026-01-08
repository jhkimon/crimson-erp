import pandas as pd

def load_excel(file):
    df = pd.read_excel(file, header=2)
    df.columns = (
        df.columns
        .str.replace("\n", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return df


def safe_str(row, col):
    val = row.get(col)
    if pd.isna(val):
        return ""
    return str(val).strip()


def safe_int(row, col):
    val = row.get(col)

    if val is None or pd.isna(val):
        return 0

    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return 0

    try:
        return int(val)
    except (ValueError, TypeError):
        raise ValueError(f"{col} 숫자 변환 실패: {val}")
