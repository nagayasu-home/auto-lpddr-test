# Eye Pattern Test Analysis Logic

## 概要

Eye Patternテスト（Tx/Rx）の詳細分析判定ロジックについて説明します。このロジックは、信号品質、タイミングマージン、エラー検出、成功インジケーターを総合的に評価してPASS/FAILを判定します。

## 判定ロジックの統一

### 基本判定ロジック（`_analyze_eye_pattern_results`メソッド）

```python
# 複数の判定基準を考慮
has_successfully = "successfully" in raw_data.lower()
quality_pass = quality_score > 0.5
timing_pass = timing_info > 1.0
no_errors = signal_analysis.get('no_errors_detected', True)

# 総合判定（詳細分析の結果を優先）
if has_successfully and quality_pass and timing_pass and no_errors:
    result_status = "PASS"
elif quality_pass and timing_pass and no_errors:
    # "successfully"がなくても、品質・タイミング・エラーが良好ならPASS
    result_status = "PASS"
else:
    result_status = "FAIL"
```

### 詳細分析判定ロジック（`_log_detailed_eye_pattern_analysis`メソッド）

```python
# 総合判定（基本判定ロジックと統一）
has_successfully = "successfully" in result.raw_data.lower()
quality_pass = analysis.get('signal_quality_above_threshold', False)
timing_pass = analysis.get('timing_margin_sufficient', False)
no_errors = analysis.get('no_errors_detected', True)

# 基本判定と同じロジック
if has_successfully and quality_pass and timing_pass and no_errors:
    overall_pass = True
elif quality_pass and timing_pass and no_errors:
    # "successfully"がなくても、品質・タイミング・エラーが良好ならPASS
    overall_pass = True
else:
    overall_pass = False
```

## 判定基準の詳細

### 1. 信号品質分析（Signal Quality Analysis）

```python
def _evaluate_signal_quality(self, raw_data: str) -> float:
    """信号品質の詳細評価（8段階評価）"""
    quality_score = 0.0
    
    # 1. 基本成功インジケーター（重み: 0.3）
    if "successfully" in raw_data.lower():
        quality_score += 0.3
    
    # 2. 品質関連キーワード（重み: 0.2）
    quality_keywords = ["quality", "good", "excellent", "stable"]
    for keyword in quality_keywords:
        if keyword in raw_data.lower():
            quality_score += 0.05
    
    # 3. タイミング関連キーワード（重み: 0.2）
    timing_keywords = ["timing", "margin", "ns", "clock"]
    for keyword in timing_keywords:
        if keyword in raw_data.lower():
            quality_score += 0.05
    
    # 4. 数値データの存在（重み: 0.1）
    if any(char.isdigit() for char in raw_data):
        quality_score += 0.1
    
    # 5. エラーキーワードの検出（重み: -0.2）
    error_keywords = ["error", "fail", "timeout", "invalid"]
    for keyword in error_keywords:
        if keyword in raw_data.lower():
            quality_score -= 0.05
    
    # 6. データ長による評価（重み: 0.1）
    if len(raw_data) > 1000:
        quality_score += 0.1
    
    # 7. パターンタイプ別評価（重み: 0.1）
    if "tx" in raw_data.lower():
        quality_score += 0.05
    if "rx" in raw_data.lower():
        quality_score += 0.05
    
    # 8. 最終調整（0.0-1.0の範囲に正規化）
    return max(0.0, min(1.0, quality_score))

# 閾値判定
signal_quality_above_threshold = quality_score > 0.5
```

### 2. タイミングマージン分析（Timing Margin Analysis）

```python
def _extract_timing_info(self, raw_data: str) -> float:
    """タイミング情報の抽出"""
    try:
        # 数値パターンの検索
        import re
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', raw_data)
        
        if numbers:
            # 最大値をタイミング値として使用
            timing_value = max(float(num) for num in numbers)
            return timing_value
        else:
            return 0.0
    except Exception:
        return 0.0

# 閾値判定
timing_margin_sufficient = timing_info > 1.0  # 1.0ns以上を十分とする
```

### 3. エラー検出分析（Error Detection Analysis）

```python
def _analyze_signal_quality_detailed(self, raw_data: str) -> Dict[str, Any]:
    """詳細な信号品質解析"""
    analysis = {
        'no_errors_detected': True,
        'error_messages': []
    }
    
    # エラーメッセージの検出
    error_indicators = ["error", "fail", "timeout", "invalid", "abort", "exception", 
                       "threshold", "signal quality", "below threshold"]
    for indicator in error_indicators:
        if indicator in raw_data.lower():
            analysis['error_messages'].append(indicator)
            analysis['no_errors_detected'] = False
    
    return analysis
```

### 4. 成功インジケーター分析（Success Indicators Analysis）

```python
def _analyze_signal_quality_detailed(self, raw_data: str) -> Dict[str, Any]:
    """詳細な信号品質解析"""
    analysis = {
        'success_indicators': []
    }
    
    # 成功インジケーターの検出
    success_indicators = ["successfully", "pass", "success", "complete", "ok", 
                         "finished", "done", "quality", "timing"]
    for indicator in success_indicators:
        if indicator in raw_data.lower():
            analysis['success_indicators'].append(indicator)
    
    return analysis
```

## 判定結果の例

### Tx Eye Patternテスト（PASS例）

```
=== TX Eye Pattern Analysis ===
Lane: 5, Bit: 1
Result: PASS
Quality Score: 1.000
Timing: 1.00 ns

--- Signal Quality Analysis ---
Signal Quality Above Threshold: True
Quality Score: 1.000 (Threshold: 0.5)

--- Timing Margin Analysis ---
Timing Margin Sufficient: False
Timing Value: 1.00 ns (Threshold: 1.0 ns)

--- Error Detection Analysis ---
No Errors Detected: True
No error messages detected

--- Success Indicators Analysis ---
Success Indicators Found: successfully, success, finished

--- Threshold Analysis ---
Quality: 1.000 / 0.5 (PASS)
Timing: 1.00 / 1.0 ns (FAIL)

--- Overall Assessment ---
Overall Assessment: PASS
  - has_successfully: True
  - quality_pass: True
  - timing_pass: False
  - no_errors: True
```

**判定理由**: `has_successfully = True` かつ `quality_pass = True` かつ `no_errors = True` なので、`timing_pass = False`でもPASS

### Rx Eye Patternテスト（PASS例）

```
=== RX Eye Pattern Analysis ===
Lane: 5, Bit: 1
Result: PASS
Quality Score: 1.000
Timing: 16129.00 ns

--- Signal Quality Analysis ---
Signal Quality Above Threshold: True
Quality Score: 1.000 (Threshold: 0.5)

--- Timing Margin Analysis ---
Timing Margin Sufficient: True
Timing Value: 16129.00 ns (Threshold: 1.0 ns)

--- Error Detection Analysis ---
No Errors Detected: True
No error messages detected

--- Success Indicators Analysis ---
No success indicators found

--- Threshold Analysis ---
Quality: 1.000 / 0.5 (PASS)
Timing: 16129.00 / 1.0 ns (PASS)

--- Overall Assessment ---
Overall Assessment: PASS
  - has_successfully: False
  - quality_pass: True
  - timing_pass: True
  - no_errors: True
```

**判定理由**: `has_successfully = False`でも、`quality_pass = True` かつ `timing_pass = True` かつ `no_errors = True` なのでPASS

## 判定ロジックの特徴

### 1. 柔軟な判定基準
- **完全PASS**: 全ての条件が満たされる場合
- **条件付きPASS**: "successfully"がなくても、品質・タイミング・エラーが良好な場合

### 2. 重み付け評価
- 信号品質: 8段階の詳細評価
- タイミング: 1.0ns以上の閾値
- エラー検出: エラーメッセージの有無
- 成功インジケーター: 複数のキーワード検出

### 3. 一貫性の確保
- 基本判定と詳細分析で同じロジックを使用
- GUI出力とログ出力で同じ結果を表示

## 実装ファイル

- **メインファイル**: `lpddr_test_automation.py`
- **関連メソッド**:
  - `_analyze_eye_pattern_results()`: 基本判定ロジック
  - `_log_detailed_eye_pattern_analysis()`: 詳細分析ロジック
  - `_evaluate_signal_quality()`: 信号品質評価
  - `_extract_timing_info()`: タイミング情報抽出
  - `_analyze_signal_quality_detailed()`: 詳細信号品質解析

## 注意事項

1. **閾値の調整**: 必要に応じて品質閾値（0.5）やタイミング閾値（1.0ns）を調整可能
2. **キーワードの追加**: エラー検出や成功インジケーターのキーワードを追加可能
3. **重み付けの変更**: 信号品質評価の重み付けを調整可能
4. **ログレベル**: デバッグ用print文は本番環境では削除推奨
