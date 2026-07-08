HAS_NLTK = False
HAS_ROUGE = False

import math

def lcs(x, y):
    n, m = len(x), len(y)
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if x[i-1] == y[j-1]:
                table[i][j] = table[i-1][j-1] + 1
            else:
                table[i][j] = max(table[i-1][j], table[i][j-1])
    return table[n][m]

def simple_rouge(reference, hypothesis):
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    if not ref_words or not hyp_words:
        class Dummy:
            def __init__(self):
                self.precision = 0.0
                self.recall = 0.0
                self.fmeasure = 0.0
        return {"rouge1": Dummy(), "rouge2": Dummy(), "rougeL": Dummy()}
        
    # ROUGE-1
    ref_unigrams = {}
    for w in ref_words:
        ref_unigrams[w] = ref_unigrams.get(w, 0) + 1
    hyp_unigrams = {}
    for w in hyp_words:
        hyp_unigrams[w] = hyp_unigrams.get(w, 0) + 1
        
    overlap_1 = sum(min(count, ref_unigrams.get(w, 0)) for w, count in hyp_unigrams.items())
    p1 = overlap_1 / len(hyp_words)
    r1 = overlap_1 / len(ref_words)
    f1_1 = 2 * p1 * r1 / (p1 + r1) if (p1 + r1) > 0 else 0.0
    
    # ROUGE-2
    ref_bigrams = {}
    for i in range(len(ref_words) - 1):
        bg = (ref_words[i], ref_words[i+1])
        ref_bigrams[bg] = ref_bigrams.get(bg, 0) + 1
    hyp_bigrams = {}
    for i in range(len(hyp_words) - 1):
        bg = (hyp_words[i], hyp_words[i+1])
        hyp_bigrams[bg] = hyp_bigrams.get(bg, 0) + 1
        
    overlap_2 = sum(min(count, ref_bigrams.get(bg, 0)) for bg, count in hyp_bigrams.items())
    p2 = overlap_2 / max(1, len(hyp_words) - 1)
    r2 = overlap_2 / max(1, len(ref_words) - 1)
    f1_2 = 2 * p2 * r2 / (p2 + r2) if (p2 + r2) > 0 else 0.0
    
    # ROUGE-L
    lcs_len = lcs(ref_words, hyp_words)
    p_l = lcs_len / len(hyp_words)
    r_l = lcs_len / len(ref_words)
    f1_l = 2 * p_l * r_l / (p_l + r_l) if (p_l + r_l) > 0 else 0.0
    
    class Score:
        def __init__(self, p, r, f):
            self.precision = p
            self.recall = r
            self.fmeasure = f
            
    return {
        "rouge1": Score(p1, r1, f1_1),
        "rouge2": Score(p2, r2, f1_2),
        "rougeL": Score(p_l, r_l, f1_l)
    }

def simple_bleu(reference, hypothesis):
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    if not ref_words or not hyp_words:
        return 0.0
        
    ref_unigrams = {}
    for w in ref_words:
        ref_unigrams[w] = ref_unigrams.get(w, 0) + 1
    hyp_unigrams = {}
    for w in hyp_words:
        hyp_unigrams[w] = hyp_unigrams.get(w, 0) + 1
        
    overlap_1 = sum(min(count, ref_unigrams.get(w, 0)) for w, count in hyp_unigrams.items())
    p1 = overlap_1 / len(hyp_words)
    
    ref_bigrams = {}
    for i in range(len(ref_words) - 1):
        bg = (ref_words[i], ref_words[i+1])
        ref_bigrams[bg] = ref_bigrams.get(bg, 0) + 1
    hyp_bigrams = {}
    for i in range(len(hyp_words) - 1):
        bg = (hyp_words[i], hyp_words[i+1])
        hyp_bigrams[bg] = hyp_bigrams.get(bg, 0) + 1
        
    overlap_2 = sum(min(count, ref_bigrams.get(bg, 0)) for bg, count in hyp_bigrams.items())
    p2 = overlap_2 / max(1, len(hyp_words) - 1)
    
    if p1 == 0 or p2 == 0:
        return 0.0
        
    bp = 1.0 if len(hyp_words) > len(ref_words) else math.exp(1 - len(ref_words)/len(hyp_words))
    return bp * math.exp(0.5 * math.log(p1) + 0.5 * math.log(p2))

def calculate_metrics(reference, hypothesis):
    # Setup BLEU
    if HAS_NLTK:
        try:
            ref_tokens = [reference.lower().split()]
            hyp_tokens = hypothesis.lower().split()
            smoothie = SmoothingFunction().method4
            bleu_score = sentence_bleu(ref_tokens, hyp_tokens, weights=(0.5, 0.5, 0, 0), smoothing_function=smoothie)
        except Exception:
            bleu_score = simple_bleu(reference, hypothesis)
    else:
        bleu_score = simple_bleu(reference, hypothesis)
    
    # Setup ROUGE
    if HAS_ROUGE:
        try:
            scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
            rouge_scores = scorer.score(reference, hypothesis)
        except Exception:
            rouge_scores = simple_rouge(reference, hypothesis)
    else:
        rouge_scores = simple_rouge(reference, hypothesis)
    
    print("\n" + "="*50)
    print("NLP EVALUATION: ROUGE & BLEU SCORES")
    print("="*50)
    
    # Print BLEU
    print(f"\n[+] BLEU Score (n-gram overlap against reference):")
    print(f"    Total BLEU: {bleu_score:.4f} / 1.0000")
    
    # Print ROUGE
    print(f"\n[+] ROUGE Scores (Recall-Oriented Understudy for Gisting Evaluation):")
    
    r1 = rouge_scores['rouge1']
    print(f"    ROUGE-1 (Unigram):   Precision: {r1.precision:.4f} | Recall: {r1.recall:.4f} | F1: {r1.fmeasure:.4f}")
    
    r2 = rouge_scores['rouge2']
    print(f"    ROUGE-2 (Bigram):    Precision: {r2.precision:.4f} | Recall: {r2.recall:.4f} | F1: {r2.fmeasure:.4f}")
    
    rl = rouge_scores['rougeL']
    print(f"    ROUGE-L (Longest):   Precision: {rl.precision:.4f} | Recall: {rl.recall:.4f} | F1: {rl.fmeasure:.4f}")
    
    print("\n" + "="*50 + "\n")

def count_syllables(word):
    word = word.lower().strip(".:,;?!()-")
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    if word[0] in vowels:
        count += 1
    for index in range(1, len(word)):
        if word[index] in vowels and word[index - 1] not in vowels:
            count += 1
    if word.endswith("e"):
        count -= 1
    if count <= 0:
        count = 1
    return count

def calculate_readability(text):
    if not text or not text.strip():
        return {"flesch_reading_ease": 0.0, "flesch_kincaid_grade": 0.0}
    import re
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    num_sentences = max(1, len(sentences))
    
    words = re.findall(r'\b\w+\b', text)
    num_words = max(1, len(words))
    
    num_syllables = sum(count_syllables(w) for w in words)
    
    asl = num_words / num_sentences
    asw = num_syllables / num_words
    
    fre = 206.835 - (1.015 * asl) - (84.6 * asw)
    fkg = (0.39 * asl) + (11.8 * asw) - 15.59
    
    return {
        "flesch_reading_ease": round(fre, 2),
        "flesch_kincaid_grade": round(fkg, 2)
    }

def validate_fhir_bundle(bundle):
    import json
    if isinstance(bundle, str):
        try:
            bundle = json.loads(bundle)
        except Exception as e:
            return 0.0, [f"Invalid JSON string: {e}"]
            
    if bundle is None:
        return 1.0, ["No lab results present (FHIR bundle is correctly null)."]
        
    if not isinstance(bundle, dict):
        return 0.0, ["FHIR bundle is not a JSON object/dictionary."]
        
    score = 1.0
    issues = []
    
    if bundle.get("resourceType") != "Bundle":
        score -= 0.2
        issues.append("Missing resourceType: 'Bundle'")
        
    if bundle.get("type") != "collection":
        score -= 0.2
        issues.append("Missing or incorrect bundle type: should be 'collection'")
        
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        score -= 0.2
        issues.append("'entry' field is not a list")
        entries = []
        
    if len(entries) == 0:
        issues.append("FHIR bundle entry list is empty")
        
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(f"Entry {idx} is not a valid JSON object")
            continue
        resource = entry.get("resource", {})
        if not isinstance(resource, dict):
            issues.append(f"Entry {idx} resource is not a valid JSON object")
            continue
            
        if resource.get("resourceType") != "Observation":
            score -= 0.1 / max(1, len(entries))
            issues.append(f"Entry {idx} resourceType is not 'Observation'")
            
        if "status" not in resource:
            score -= 0.1 / max(1, len(entries))
            issues.append(f"Entry {idx} is missing 'status' field")
            
        if "code" not in resource:
            score -= 0.1 / max(1, len(entries))
            issues.append(f"Entry {idx} is missing 'code' field")
            
    return max(0.0, round(score, 2)), issues

if __name__ == "__main__":
    
    # --- GROUND TRUTH (Reference) ---
    reference_medical_plan = """
    Document Detected: Blood Test Report
    Health Status: Needs Attention
    Doctor Visit: See an Endocrinologist within 2 weeks.
    At your age, elevated HbA1c specifically increases long-term optic nerve and cardiovascular risk.
    You must eat bitter gourd, ragi, and spinach. Avoid refined sugar and potatoes.
    Daily habits: Walk 30 minutes rapidly every morning.
    Myth Buster: Jaggery is NOT safer than white sugar for a diabetic level this high.
    Warning signs: If you experience sudden extreme dizziness or blurred vision, go to hospital immediately.
    """
    
    # --- LLM GENERATED (Hypothesis) ---
    generated_ai_plan = """
    Document Detected: Blood Test
    Health Status: Needs Attention
    Doctor Visit: You should consult an Endocrinologist within 2 weeks.
    Age Context: At 45, high HbA1c drastically raises risks of eye and heart damage.
    Foods to eat: Bitter gourd, ragi, palak (spinach). 
    Foods to avoid: Sugar, maida, potatoes.
    Daily habit: 30 mins brisk walking every day.
    Myth Buster: People say jaggery is healthy for diabetics, but it spikes sugar exactly like white sugar.
    Warning signs: Sudden dizziness or blurry vision means immediate hospital visit.
    """
    
    print("Executing Medical AI Text Evaluation...")
    print("Comparing Generated Gemini Output against Clinical Reference Standard...\n")
    
    calculate_metrics(reference_medical_plan, generated_ai_plan)
    
    print("Testing Readability Calculator:")
    readability_scores = calculate_readability(generated_ai_plan)
    print(f"Flesch Reading Ease: {readability_scores['flesch_reading_ease']}")
    print(f"Flesch-Kincaid Grade: {readability_scores['flesch_kincaid_grade']}")

