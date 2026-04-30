import sys
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer

def calculate_metrics(reference, hypothesis):
    # Setup BLEU
    ref_tokens = [reference.lower().split()]
    hyp_tokens = hypothesis.lower().split()
    smoothie = SmoothingFunction().method4
    
    # Calculate BLEU (using bigram weighting to be fair on short outputs)
    bleu_score = sentence_bleu(ref_tokens, hyp_tokens, weights=(0.5, 0.5, 0, 0), smoothing_function=smoothie)
    
    # Setup ROUGE
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    rouge_scores = scorer.score(reference, hypothesis)
    
    print("\n" + "="*50)
    print("📈 NLP EVALUATION: ROUGE & BLEU SCORES")
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
