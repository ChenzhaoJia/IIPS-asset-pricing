"""Restore the full Annual Review source and add explanations and frozen topic results.

Editorial reconstruction, not an estimation script. Original table bodies and
conclusion are checked for preservation by check_manuscript_preservation.py.
"""
from pathlib import Path
import shutil

R = Path(__file__).resolve().parents[1]
B = R / 'drafts/annual_review_pdf_baseline'
M = R / 'drafts/manuscript'


def run():
    s = (B / 'main.tex').read_text(encoding='utf-8-sig')
    # Four grammatical singulars are transcribed literally in the PDF baseline.
    s = s.replace('pricing implication of', 'pricing implications of')
    s = s.replace('their market implication.', 'their market implications.')
    shutil.copy2(B / 'references.bib', M / 'references.bib')
    shutil.copytree(B / 'figures', M / 'figures', dirs_exist_ok=True)

    def change(old, new):
        nonlocal s
        assert s.count(old) == 1, (old[:120], s.count(old))
        s = s.replace(old, new, 1)

    change('We develop the Effective Sentiment Index to combine',
           'We develop the Effective Sentiment Index (ESI) to combine')
    change(r'13.4\% (q5 alpha)', r'13.4\% (alpha relative to the augmented q-factor model)')
    change('Its annualized q5 alpha is about',
           'Its annualized alpha relative to the augmented q-factor model (q5) is about')
    change('the interaction between these two market participants remains underexplored.',
           'it remains unclear how the content of a managerial response should be evaluated in relation to the concern that prompted it. A matched dialogue observes both the demand for clarification and the response to that demand. This motivates our question: does the joint interpretation of the two sides contain return information beyond either side in isolation?')
    change('Second, the market microstructure in China facilitates the examination of sentiment effects.',
           'Second, the Chinese market provides a setting in which to compare information in interactive text with trading pressure associated with investor attention.')
    change('The resulting measure provides persistent information about subsequent stock returns.',
           'The resulting measure provides persistent information about subsequent stock returns. In particular, question volume scales investor tone, while reply substantiveness and the initial investor state determine the weight on managerial tone. This construction makes the dialogue context explicit rather than treating the two texts as interchangeable sentiment observations.')
    change('Our study shifts the focus to stock return prediction and shows that interactive text predicts returns beyond the comparison variables included in our baseline regressions.',
           'Our study shifts the focus to stock return prediction and shows that interactive text predicts returns beyond the comparison variables included in our baseline regressions. We compare ESI with investor tone, managerial tone, and their simple average, report both equal- and value-weighted portfolios, and use conditional double sorts to examine the three interaction features entering the index.')

    old = r'We also obtain the daily China factor series for the Fama-French three-factor model (FF3), the Liu-Stambaugh-Yuan four-factor model (CH4), and the augmented q-factor model (q5) from CSMAR \citep{fama1993common,hou2021,liu2019}. '
    change(old, '')
    change(r'\subsection{Construction of ESI}\label{sec:esi_construction}', r'''\paragraph{Matching a question to its reply and assigning the observation date.}
Replies can arrive after the question, so the date to which a dialogue is assigned must be distinguished from the date on which the reply becomes public. We retain the question--reply links supplied in each platform record. We then group the linked records by firm and question date. Investor tone is averaged over the questions in that group; managerial tone and reply substantiveness are aggregated from their corresponding replies. Thus the two inputs are aggregated separately within the same matched question-date cohort. They are not independently pooled from all questions and all replies posted by a firm on the same calendar date.

For example, if a question is posted on Day 1 and its linked reply arrives on Day 3, the original construction assigns both text inputs to the Day 1 cohort. The reply does not become a second, unrelated Day 3 input merely because it is posted on that date. If a firm receives several questions on Day 1, their own linked replies enter that cohort even when those replies arrive on different dates. A reply to an earlier question belongs to that earlier question-date cohort. ESI requires its tone, substantiveness, and attention inputs; a missing input is not filled with a neutral zero.

This convention measures the content of the completed dialogue retrospectively. In the original question-date O2C tests, a reply arriving on Day 3 was not necessarily observable before the Day 2 return. The timing checks in Appendix Table \ref{tab:horizon_robustness} and the separately labeled public-availability C2C topic supplement distinguish dialogue attribution from information availability. The original question-date return results are retained; the date convention should not be interpreted as making a late reply publicly observable earlier.

\subsection{Construction of ESI}\label{sec:esi_construction}

The construction has three steps. First, score the linked question and reply, and aggregate their scores within the firm--question-date cohort. Second, summarize attention by question volume and scale managerial tone using its sample distribution. Third, combine the attention-weighted investor component with managerial tone weighted by reply substantiveness and the initial investor state. The equations below describe these weights; Appendix Table \ref{tab:parameters} reports the distributional quantities used to implement them.
''')
    change(r'We set $\lambda=0.5$ and $\gamma=5$ in the baseline specification.', r'''We set $\lambda=0.5$ and $\gamma=5$ in the baseline specification.

These constants have distinct roles. With normalized attention between zero and one, $\lambda=0.5$ allows the investor component to rise from its unscaled value to 1.5 times that value. The constant $\gamma=5$ sets the relative scale of the standardized managerial component after substantiveness and state weighting. The anchor $q=0.30$ places the peak state weight at the 30th percentile of investor tone, and $b=0.8$ sets the kernel bandwidth to 0.8 investor-tone standard deviations. Neither the kernel nor this quantile choice assumes normally distributed tone. These are the retained baseline design constants, not estimates of structural economic parameters or a claim that a unique optimal specification has been identified.

The centering, dispersion, quantile, and attention normalization use the full original 2010--2024 text pools. They do not use a 2010--2018 training window. Because the original regression and portfolio preparation rules yield different eligible pools, their distributional scales are reported separately in Appendix Table \ref{tab:parameters}; the constants remain the same. Figure \ref{fig:tone_kde} and Table \ref{tab:summary_stats} describe the underlying distributions, while Appendix Table \ref{tab:grid_search_summary} retains the original sensitivity results. Full-sample normalization is part of this historical specification and is not an out-of-sample calibration exercise.\footnote{The original implementation also suppresses a negative managerial contribution when investor tone is positive: $\widetilde G=0$ if $I>0$ and $G<0$, and $\widetilde G=G$ otherwise, with $\widetilde G$ used in the implemented index. This implementation convention is retained with the historical results; no parameters or observations are changed in this revision.}
''')
    change('It also reduces exposure to overnight price movements that investors could not trade after observing the interaction',
           'It focuses the outcome on the next intraday interval; the question-date assignment described above separately determines whether the complete dialogue was already public')
    change(r'\section{Baseline return predictability}\label{sec:baseline_return_predictability}', r'''\subsection{Content and question nature classification}\label{sec:topic_classification}

To describe what investors ask and how managers respond, we supplement the tone measures with automated classification along two distinct dimensions: 19 content themes describe the subject discussed, and five question-nature categories describe the purpose of an inquiry. The completed pipeline uses Qwen3 text embeddings and supervised classification with a fixed taxonomy. It is not an unsupervised discovery of latent topics. Content is classified separately for questions and replies; question nature is classified on the question side. These classifications do not replace either the sentiment scores or the Random Forest substantiveness scores entering the baseline ESI.

The full archive contains 5,836,158 paired source records, including 5,836,155 nonempty questions. This archive is larger than the return-regression sample because classification does not require matched market outcomes or regression controls. Figure \ref{fig:full_topic_classification} shows content and question-nature distributions. At the retained content-score threshold, 54.54\% of questions and 64.49\% of replies receive a content assignment. The remaining records retain explicit low-score, generic-template, context-dependent, or empty-text statuses, as appropriate; Appendix Table \ref{tab:full_topic_coverage} reports their coverage. These shares describe model assignments and are not measures of classification accuracy.

On the question side, the nature categories comprise explanations or clarifications (81.56\%), corrections of misunderstandings (3.34\%), verification of rumors (1.41\%), requests for undisclosed information (3.82\%), and suggestions or other inquiries (9.88\%). Rounding accounts for the sum differing slightly from 100\%. The fourth label, abbreviated as ``inappropriate questions'' in the figure, denotes a review category for requests for undisclosed information, not a confirmed finding of misconduct. Assistant-provided supervision and retained model scores do not substitute for independent human validation. Appendix \ref{app:topic_examples} gives Chinese source excerpts, English summaries, and classification rationales covering all 19 themes and five nature categories.

\section{Baseline return predictability}\label{sec:baseline_return_predictability}''')
    change(r'We report equal weight (EW) and value weight (VW) long minus short returns, annualized performance, and alphas from the CH4 and q5 models.', r'''We report equal weight (EW) and value weight (VW) long minus short returns, annualized performance, and alphas from the CH4 and q5 models.\footnote{CH4 is the China factor benchmark following \citet{liu2019}. The historical q5 series is the U.S. Global-q augmented q-factor model following \citet{hou2021}; it is not a Chinese CSMAR q5 series. We retain the original q5 results as a separate comparison rather than relabeling their geography. A domestic FF3 comparison is a distinct specification.}''')
    # Preserve all historical estimates while making the known earnings date explicit.
    change('on ESI measured before the earnings announcement.', r'''on ESI measured before the historical earnings-event date.\footnote{The retained Annual Review SUE results use the source update date as the event reference. That date is not necessarily the actual announcement date (\texttt{Annodt}). References to announcement timing in the inherited specification describe its original intended interpretation; these coefficients should not be presented as a verified true-announcement-date test. This revision preserves the historical table and does not replace a true-announcement-date result with it.}''')
    change('$t_h$ is its announcement date.', '$t_h$ is the historical earnings-event date described above.')
    change('To test whether platform interactions predict these future fundamental surprises, we estimate the following regression.',
           'To test whether platform interactions predict these future fundamental surprises, we estimate the following regression:')
    change('Accordingly, we estimate the panel regression for each order type and horizon as follows:',
           r'We also define the paired difference as $OIB^{diff}=OIB^{inst}-OIB^{ind}$ before estimation. Large and small order groups are size-based proxies rather than observed investor account identities. The five-day outcome below is the mean daily imbalance over days $t+1$ through $t+5$, not a cumulative imbalance. Accordingly, we estimate the panel regression for each order type and horizon as follows:')
    change(r'\section{Conclusion}\label{sec:conclusion}', r'''\subsection{Exploratory return slopes across content themes}\label{sec:topic_slopes}

The completed content classification also permits an exploratory examination of whether the ESI slope differs across the concerns raised by investors. This supplement uses the existing public-availability C2C specification, rather than reinterpreting the original question-date O2C estimates as the same test. Text inputs are dated after the matched replies become available. The outcome is the next-day close-to-close excess return; it is not a CH4-residualized return. The supplement retains its own previously frozen historical calibration, including $\lambda=0.4811$, $\gamma=3.0495$, and $b=0.7425$, rather than substituting the original baseline constants. Thus differences from the main results can reflect timing, return definition, calibration, and sample eligibility as well as content.

For availability-date firm observations, let $D^k_{i,t}$ identify the dominant question-content category. Dominance is determined by the largest category count, including unclassified records. With unclassified or low-score content as the reference category, we estimate
\begin{equation}\label{eq:topic_slopes}
\begin{split}
r^{C2C,excess}_{i,t+1}={}&\mu_i+\tau_t+\beta_0 ESI^z_{i,t}
+\sum_{k=1}^{19}a_kD^k_{i,t}\\
&+\sum_{k=1}^{19}\delta_k(ESI^z_{i,t}D^k_{i,t})
+\boldsymbol{c}'\mathbf X_{i,t}+\varepsilon_{i,t+1}.
\end{split}
\end{equation}
Here $ESI^z$ is standardized with the retained historical scale, and $\mathbf X$ contains the supplement's controls. A second specification additionally includes investor and managerial tone. Firm and date fixed effects are included, with standard errors clustered by firm and date. The category-specific slope is $\beta_0+\delta_k$; the reference slope is $\beta_0$.

Appendix Table \ref{tab:full_topic_heterogeneity} reports all category slopes in basis points per ESI standard deviation. Products or business has a positive slope of 2.02 ($t=3.40$) in the specification without the two separate tones. The slope is 1.12 ($t=1.25$) after both tones are added. The BH $p$ column reports Benjamini--Hochberg multiple-testing adjustments for all category slopes in that latter specification, rather than a test of differences across categories. The separate joint Wald test evaluates $H_0:\delta_1=\cdots=\delta_{19}=0$; its $p$-values are 0.865 and 0.873. These tests do not reject equal slopes across themes. Accordingly, this content analysis adds descriptive interpretation and exploratory estimates to the original results, without claiming that the strongest individual slope establishes a different return mechanism.

\section{Conclusion}\label{sec:conclusion}''')
    figure = r'''
\begin{figure}[H]
\centering
\includegraphics[width=\textwidth,height=0.68\textheight,keepaspectratio]{figures/full_content_and_nature_distribution.png}
\caption{Automated Content and Question Nature Classification}\label{fig:full_topic_classification}
\begin{minipage}{\textwidth}\small\justifying
Panel A reports the 19 fixed content themes separately for questions and replies, using 5,836,158 source records on each side. Panel B reports question-nature candidates among 5,836,155 nonempty questions. Unassigned content and review flags are retained; coverage is distinct from accuracy. The fourth nature category denotes requests for undisclosed information and does not establish a disclosure violation. The taxonomy uses assistant supervision and requires independent human validation. The full classification was completed before this revision; no records were reclassified to obtain these results.
\end{minipage}
\end{figure}
\clearpage
'''
    change(r'\begin{table}[H]'+'\n  '+r'\centering'+'\n  '+r'\caption{Descriptive Statistics of Main Variables}',
           figure+r'\begin{table}[H]'+'\n  '+r'\centering'+'\n  '+r'\caption{Descriptive Statistics of Main Variables}')
    change(r'\section{Textual analysis methodology} \label{app:nlp_methodology}', r'''\input{tables/full_topic_heterogeneity}
\clearpage
\input{tables/full_topic_coverage}
\clearpage
\input{tables/parameters}
\clearpage

\section{Textual analysis methodology} \label{app:nlp_methodology}''')
    change('leaving 2,000 interactions for the substantiveness classifier.',
           'leaving 1,999 usable interactions for the substantiveness classifier.')
    anchor = r'\section{Variable definitions} \label{app:variable_definitions}'
    # Insert before the C-table counter reset, so the supplementary benchmark is B1.
    old = r'\clearpage'+'\n'+r'\setcounter{table}{0}'+'\n'+r'\renewcommand{\thetable}{C\arabic{table}}'
    change(old, r'''\paragraph{Comparison on a common holdout.}
To compare the substantiveness measurement across model families, we retain the completed benchmark using the same 402 labeled test pairs for Random Forest, Chinese BERT, and a local instruction language model. This benchmark uses a template-separated split of the 1,999 usable labeled pairs, with 1,280 training and 317 validation pairs; it is distinct from the original production fitting procedure above. Table \ref{tab:substantiveness_benchmark} reports discrimination and calibration measures. BERT performs better on these existing labels, but this comparison does not change the production Random Forest scores used in the original return tables. Independent semantic validation remains a separate task.
\setcounter{table}{0}
\renewcommand{\thetable}{B\arabic{table}}
\renewcommand{\theHtable}{B\arabic{table}}
\input{tables/classifier_benchmark}
\clearpage
\setcounter{table}{0}
\renewcommand{\thetable}{C\arabic{table}}''')
    change(r'\bibliographystyle{elsarticle-harv}', r'''\subsection{Content and question-nature examples}\label{app:topic_examples}
\input{tables/topic_nature_examples_2026-10-12}
\clearpage
\bibliographystyle{elsarticle-harv}''')
    # Preserve the original table body, while relieving its crowded bottom note.
    import re
    for block in re.findall(r'\\begin\{table\}.*?\\end\{table\}', s, re.S):
        if r'\label{tab:kernel_robustness}' in block:
            s = s.replace(block, '\\begingroup\n\\setstretch{1.1}\n' + block + '\n\\endgroup')
    s = s.replace(r'\begin{document}', '\\setlength{\\emergencystretch}{1em}\n\\begin{document}', 1)
    (M / 'main.tex').write_text(s, encoding='utf-8')
    print('Restored full Annual Review source with additive explanations and topic supplement.')


if __name__ == '__main__':
    run()
