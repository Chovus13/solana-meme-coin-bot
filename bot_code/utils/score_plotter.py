import matplotlib.pyplot as plt
import os

def plot_token_scores(token_symbol: str, safety_score: int, ai_score: float, market_score: float):
    labels = ['Safety', 'AI Pred.', 'Market']
    values = [safety_score, ai_score * 100, market_score * 100]
    colors = ['#4CAF50', '#2196F3', '#FF9800']

    os.makedirs('reports', exist_ok=True)

    plt.figure(figsize=(6, 4))
    bars = plt.bar(labels, values, color=colors)
    plt.ylim(0, 100)
    plt.title(f'Score Breakdown for {token_symbol}', fontsize=14)
    plt.ylabel('Score (%)')
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., height + 2, f'{height:.1f}%', ha='center', fontsize=10)

    plt.tight_layout()
    output_path = os.path.join('reports', f'{token_symbol}_score.png')
    plt.savefig(output_path)
    plt.close()
    return output_path