# TD 2 Plenary Presentation: Quorum Voting, False Consensus & Dynamic Routing

**Sub-group**: DIA 3 - Group 2  
**Session Date**: 2026-11-18 (17:15 - 17:30)  
**Course**: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  
**Audience**: Course Instructors & Peer Sub-groups  

---

## 1. Executive Summary (The 30-Second Elevator Pitch)

> "In production AI engineering, trusting a single model draw or assuming that multiple models agreeing implies ground truth are both fatal fallacies. On question C09, two different model families agreed on an identical wrong value ($0$ cts), producing a false consensus in a 2-of-3 panel. By moving to a 3-of-5 quorum, we successfully eliminated this false consensus into a safe abstention. Furthermore, our empirical routing policy proves that while free lightweight models handle 100% of date and product filters, no free model can safely handle completed age arithmetic alone. This sets the exact price of checking for TD 3."

---

## 2. Three-Slide Plenary Presentation Structure

### Slide 1: The Voting Quorum (2-of-3 vs. 3-of-5)
* **What we built**: Implemented `vote_k_sur_n` with strict majority ($n//2 < k \le n$), provider unicity, and fail-safe abstention (unexecuted models stay in $n$ but cast 0 votes).
* **The 20-Question Benchmark**:
  - **17/20 consensus reached** in both configurations (85% automated decision rate).
  - **False Consensus on C09 in 2-of-3**: `cohere` (0) and `qwen` (0) formed a majority against `gpt-oss-120b` (487,980), accepting an erroneous answer (5% critical failure rate).
  - **Overturned in 3-of-5**: With `gpt-oss-20b` (487,980) and `dots` (`sql_rejected`), the tie 2 vs 2 fell short of $k=3$, successfully converting a financial loss into a **safe abstention**!
  - **Consensus Recovered on C19**: Dispersion 1-1-1 in 2-of-3 turned into a valid 3/5 consensus (1,990 cts) in 3-of-5.
  - **Net Result**: 3-of-5 achieves **100% precision on reached consensus** (0% false consensus).

### Slide 2: Root-Cause SQL Diagnostics & Delta Query (Case C09)
* **The Question**: Revenue from customers exactly 25 years old on 2026-09-26 (Reference: **487,980 cents**).
* **Why did two models agree on 0? (The Attractor State)**:
  - `cohere/north-mini-code`: subtracted birth year strings without subtracting from 2026. Filter matched 0 rows.
  - `qwen/qwen3.8-27b`: confused order date with reference date, and formed a contradictory anniversary window `md >= birth_md AND md < birth_md`. Filter matched 0 rows.
  - In SQL, `COALESCE(SUM(...), 0)` transforms *any* empty row set into `0`. **Two completely different bugs converged on the same numerical attractor state: 0.**
* **The Delta SQL Proof on `data/boutique.sqlite`**:
  - Executed query isolating the exact customers born between `2000-09-27` and `2001-09-26`:
    - C001 (135,000 cts), C002 (25,920 cts), C003 (47,900 cts), C007 (118,740 cts), C008 (99,090 cts), C009 (61,330 cts).
    - **Total Gap = 487,980 − 0 = 487,980 cents** (exact reconciliation to the cent).

### Slide 3: Dynamic Routing Policy & "The Price of Checking"
* **Empirical Mapping per Family**:
  - **F1 (Period) & F3 (Product)**: 100% accuracy across free models $\rightarrow$ Dispatched to cheapest free models (`gpt-oss-20b`, `qwen3.8-27b`), zero checking needed for internal dashboards.
  - **F2 (Age at Reference Date)**: Only **`openai/gpt-oss-120b`** achieved 100% (4/4). All smaller models failed or produced false consensus.
* **The Price of Checking (The Bridge to TD 3)**:
  - Because **no free model is sufficient on its own for age calculations**, production architectures must pay for verification:
    1. **Deterministic check**: local reference SQL query (0 token cost).
    2. **Paid model fallback**: `openai/gpt-oss-120b` on OpenRouter at **0.000711 USD/request**.
    3. **Human review**: mandatory for high-stakes payouts.
* **Simulator Priority Insight**:
  - In `atelier-routage.py`, an included subscription (`cash == 0, allocation > 0`) is prioritized over deferring for a free refill because subscription capacity carries zero marginal cost ("use it or lose it") and avoids the risk of deferred requests waking up to another HTTP 429 quota block.

---

## 3. Speaking Script for Plenary Presenter (3-Minute Verbatim)

> "Bonjour à tous. Pour le groupe DIA 3, nous avons démontré expérimentalement aujourd'hui deux réalités fondamentales :
> 
> Première réalité : **Le consensus n'est pas une preuve de vérité terrain.**
> Sur la question C09, notre panel 2-sur-3 a validé un chiffre de 0 centime avec 2 voix sur 3, contre une référence de 487 980 centimes. Deux modèles distincts, Cohere et Qwen, ont commis deux erreurs SQL totalement différentes qui ont toutes deux produit un ensemble vide. En SQL, le `COALESCE(SUM, 0)` agit comme un attracteur universel : n'importe quelle clause contradictoire renvoie 0. Nous avons prouvé la source de cette divergence en SQL sur `boutique.sqlite`, en isolant exactement les 6 clients et 487 980 centimes manquants.
> En passant à un quorum 3-sur-5 avec un seuil strict $k=3$, ce faux consensus a été neutralisé et converti en abstention sûre, éliminant 100% des erreurs critiques sur notre jeu de 20 questions.
> 
> Deuxième réalité : **La règle de routage et le coût de vérification pour le TD 3.**
> Nos traces montrent que les modèles légers gratuits sont parfaits (100%) sur les filtres de dates et de produits (F1 et F3). En revanche, sur le calcul d'âge révolu (F2), seul GPT-OSS 120B est fiable à 100%. Aucun modèle gratuit ne suffit seul pour des chiffres clients ou des paiements. Cela fixe directement le prix de la vérification pour le TD 3 : soit une requête SQL déterministe locale à coût nul, soit un fallback payant sur OpenRouter à 0.000711 dollar par requête."
