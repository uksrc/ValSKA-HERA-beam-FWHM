=================
Validation Primer
=================

About This Primer

This page provides a high-level introduction to the science validation work carried out by the UKSRC-ST team. It is intended for stakeholders, collaborators, and contributors who want to understand *what validation is*, *why it matters*, and *how it is implemented* in the context of precision science with the SKA and its precursors.

Whether you are a scientist, instrument team member, or programme manager, this primer aims to clarify how validation supports your work -- from model reliability to science decision-making.

For a more detailed discussion of validation in the context of precision astrophysics and cosmology see e.g. `Aguirre+22 <https://arxiv.org/abs/2104.09547>`__, `Sims+25a <https://arxiv.org/abs/2502.14029>`__, `b <https://arxiv.org/abs/2506.20042>`__ and references therein.

🔍 1. What is Validation?
=========================

In the context of radio astronomy and big-data science, **validation** is the process of determining whether our models, pipelines, and simulations can be trusted to deliver accurate and reliable scientific results.

Put simply:

   **Validation ensures that the tools we use to interpret data actually work for the science we care about.**

Validation plays a different role from **verification**:

+------------------+------------------------------------------------+----------------------------------------------------------------------------+
| Term             | Question Answered                              | Example                                                                    |
+==================+================================================+============================================================================+
| **Verification** | “Did we build the system right?”               | Does the power spectrum pipeline run without errors on test data?          |
+------------------+------------------------------------------------+----------------------------------------------------------------------------+
| **Validation**   | “Did we build the right system (for science)?” | Can we recover a known cosmological 21-cm signal from realistic mock data? |
+------------------+------------------------------------------------+----------------------------------------------------------------------------+

In the SKA context, this means asking:

-  Is our knowledge of the instrument (e.g. beam, layout, calibration) good enough for the highest precision science cases?

-  Are our simulations and pipelines accurate representations of the real sky and telescope?

-  Can we confidently go beyond the current observational and modelling frontier to detect and interpret never-before-seen faint signals?

Because real SKA and precursor data are complex and contaminated with systematics (e.g. foregrounds, calibration errors, instrumental effects), validation gives us a principled way to:

-  Quantify our confidence in detections or upper limits.

-  Identify and mitigate potential sources of bias.

-  Set requirements on instrument performance and data quality.

**Key takeaway:**

   We validate to ensure that *precision astrophysics is built on solid foundations*. Without validation, even sophisticated analyses can lead to incorrect or misleading conclusions.

| 

🎯 2. Why is Validation Critical for SKA Science?
=================================================

Modern radio cosmology aims to detect some of the faintest signals ever measured -- such as the redshifted 21-cm line of neutral hydrogen from the early Universe -- using increasingly complex instruments and analysis pipelines. In this regime, it is the meticulous characterisation of the instrument and high fidelity modelling of the data that presents the greatest challenge, not intrinsic instrumental sensitivity. **Precision science requires precision validation**.

🚨 The Challenge
~~~~~~~~~~~~~~~~

Many of the most important SKA and precursor science goals, such as probing the Epoch of Reionization (EoR), measuring Baryon Acoustic Oscillations or constraining properties of dark matter and gravity, rely on:

-  Detecting extremely weak signals (e.g. the 21-cm power spectrum is >10\ :sup:`5`\ × fainter than foregrounds)

-  Modelling instruments with complex, evolving systematics (e.g. beam chromaticity, mutual coupling)

-  Separating multiple overlapping signal components in the data (e.g. cosmological signal, sky foregrounds, instrument noise, systematics)

These challenges introduce **failure modes** that are hard to detect without formal validation:

+-------------------------------------------------+-------------------------------------------------+
| **Failure Mode**                                | **Impact on Science**                           |
+=================================================+=================================================+
| Spurious detections from unmodelled systematics | False positives or biased inferences            |
+-------------------------------------------------+-------------------------------------------------+
| Overfitting noise or foregrounds                | Signal suppression and loss of sensitivity      |
+-------------------------------------------------+-------------------------------------------------+
| Mischaracterised instrument response            | Incorrect astrophysical parameter estimation    |
+-------------------------------------------------+-------------------------------------------------+
| Foreground leakage into cosmological modes      | Invalid upper limits, contaminated measurements |
+-------------------------------------------------+-------------------------------------------------+

--------------

🧪 The Role of Validation
~~~~~~~~~~~~~~~~~~~~~~~~~

Validation mitigates these risks by testing whether our models and analysis pipelines are **good enough for the science goal at hand**. For SKA and precursor science, this involves:

-  **Simulating realistic observations**, including known sky, instrument, and noise models

-  **Processing those simulations** through the full analysis pipeline

-  **Comparing the output** to the known input to check for bias, loss, or spurious structure

These tests can be done at multiple levels:

-  **Module-level**: Does this beam model correctly simulate primary beam effects?

-  **Pipeline-level**: Does the entire pipeline recover the input Signal of Interest (SOI) within expected uncertainty?

-  **Bayesian model-level**: Does our inference framework favour the correct model when presented with SOI-free data?

--------------

📌 Why Stakeholders Should Care
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Validation provides **evidence-based confidence** that:

-  Instrument specs (e.g. beam FWHM accuracy, antenna layout) are sufficient

-  Science pipelines are not introducing systematic biases

-  Reported results -- such as detections or upper limits -- are **credible**

| It also helps set priorities:
| If validation shows a particular systematic effect (e.g. beam mischaracterization) dominates the science error budget, this can guide investments in better measurements or modelling.

   **Without validation, we’re building science conclusions on untested assumptions. With validation, we make those assumptions testable -- and trustworthy.**

| 

🧪 3. Types of Validation We Perform
====================================

Validation within the Science Validation Tooling (UKSRC-ST) team is structured across **multiple layers** of the analysis pipeline, from individual components to end-to-end science inferences. This layered approach ensures that each part of the system -- and their interactions -- are tested for reliability, accuracy, and scientific credibility.

| 

--------------

🧩 A. **Module-Level Validation**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   *"Does each component do what it claims to do?"*

We perform controlled, unit-style validation on individual simulation and modelling tools. These are often benchmarked against analytic solutions or cross-validated between simulators.

**Examples:**

-  Testing ``pyuvsim`` and ``fftvis`` against known visibility solutions (e.g. point sources, Gaussian beams)

-  Verifying beam model perturbations produce expected changes in effective FWHM

-  Cross-checks between ``OSKAR``, ``pyuvsim``, and ``matvis`` for sky model consistency

--------------

🔁 B. **Pipeline-Level (End-to-End) Validation**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   *"If we feed in a known sky and instrument model, do we recover the expected science result?"*

End-to-end tests allow us to measure the overall performance of the pipeline under realistic conditions. These simulations mimic the full complexity of the observing process, including sky foregrounds, instrument effects, and noise.

**Examples:**

-  Injecting a known 21-cm signal into a realistic HERA simulation and checking whether it is recovered

-  Measuring signal loss, bias, or foreground leakage across the pipeline

-  Comparing different calibration schemes to assess robustness of power spectrum estimates

This approach was central to the **HERA Phase I validation** effort (`Aguirre+2022 <https://arxiv.org/abs/2104.09547>`__), which uncovered subtle scale-independent signal loss and informed the development of a robust analysis framework.

--------------

📊 C. **Model Validation in a Bayesian Framework**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   *"Is the model structure itself trustworthy for science inference?"*

We apply formal Bayesian model comparison techniques to determine whether models can be trusted to yield unbiased science results. This includes:

✅ **Bayes-Factor-Based Model Comparison (BFBMC)**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Used to rank models based on their statistical consistency with the data -- especially useful for comparing cosmological models under similar assumptions.

🚫 **Limitations of BFBMC**
^^^^^^^^^^^^^^^^^^^^^^^^^^^

BFBMC alone cannot always detect when signal components are **biased by interactions with unmodelled systematics** (e.g. residual foreground structure leaking into cosmological modes).

--------------

🧰 D. **BaNTER: Bayesian Null Test Evidence Ratio**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

   *"Can this model be trusted before seeing the signal?"*

We use the **BaNTER validation framework** (`Sims+2025 <https://arxiv.org/abs/2502.14029>`__) to assess the risk of biased inference *before* using a model on real data. It compares how well composite models fit **signal-free** validation data and identifies whether the nuisance model is sufficient.

**Key idea:**

   If a composite model fits signal-free data better than the nuisance model alone, it may falsely attribute residuals to the signal -- leading to bias.

BaNTER provides a **model validation prior**, which is then used to weight model comparisons and ensure robust science inference.

--------------

📈 Summary Table
~~~~~~~~~~~~~~~~

| 

+-------------------------------+----------------------------------------------+----------------------------------------------+
| **Type of Validation**        | **Goal**                                     | **Tools**                                    |
+===============================+==============================================+==============================================+
| **Module-level**              | Test correctness of simulation components    | ``pyuvsim``, ``fftvis``, analytic benchmarks |
+-------------------------------+----------------------------------------------+----------------------------------------------+
| **Pipeline-level**            | Recover known inputs from full simulations   | End-to-end simulations, power spectra        |
+-------------------------------+----------------------------------------------+----------------------------------------------+
| **Bayesian model comparison** | Rank models based on evidence (predictivity) | ``BayesEoR``, ``PolyChord``                  |
+-------------------------------+----------------------------------------------+----------------------------------------------+
| **BaNTER**                    | Assess model credibility before inference    | Null tests, posterior odds adjustment        |
+-------------------------------+----------------------------------------------+----------------------------------------------+

--------------

| 

🛠️ 4. Our Approach
==================

Our validation strategy is **modular, layered, and Bayesian**. It combines domain-specific simulation tools with statistical rigor to build stakeholder confidence in the reliability of our science pipelines.

🧱 Modular Testing and Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We validate individual components -- such as simulators, sky models, and instrument configurations -- before integrating them into full pipelines.

**Benefits:**

-  Easier to identify the source of bugs or biases

-  Encourages reuse and reproducibility

-  Scales to increasingly complex science cases

--------------

🧪 End-to-End Simulations
~~~~~~~~~~~~~~~~~~~~~~~~~

We simulate full observing scenarios using realistic sky models, beam models, array layouts, and thermal noise. These simulations are processed using the exact same pipeline used for real data.

   🎯 *If an SKA or precursor pipeline cannot recover a known input from a simulation, it cannot be trusted to recover unknown inputs from real data.*

Key tools:

-  ``pyuvsim``, ``fftvis``, ``OSKAR`` (for visibility simulation)

-  ``BayesEoR``, ``PolyChord`` (for Bayesian inference)

-  Custom parameter sweep + perturbation frameworks (e.g. beam FWHM studies)

--------------

🧠 Bayesian Inference and Model Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than relying on visual inspection or point estimates, we use **Bayesian inference** to:

-  Quantify parameter uncertainties

-  Compare competing models via evidence

-  Identify risk of bias due to model mis-specification (e.g. foreground leakage, calibration errors)

We extend this with the **BaNTER** framework, which allows us to validate models on signal-free data *before* using them for inference.

--------------

💻 Our Infrastructure
~~~~~~~~~~~~~~~~~~~~~

Validation requires reproducibility, scalability, and traceability. We use a modern, science-friendly stack:

+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
| **Component**                     | **Details**                                                                                                                             |
+===================================+=========================================================================================================================================+
| **Computing**                     | HPC access via **Azimuth** and **Galahad** (incl. CPU and GPU nodes for accelerated computation )                                       |
+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
| **Versioning**                    | All validation code tracked in UKSRC GitHub repos (e.g. ```ValSKA-HERA-beam-FWHM`` <https://github.com/uksrc/ValSKA-HERA-beam-FWHM>`__) |
+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
| **Workflow**                      | Notebooks for exploratory work, containers (Docker/Singularity) for reproducibility                                                     |
+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
| **Agile Tracking**                | .. container:: content-wrapper                                                                                                          |
|                                   |                                                                                                                                         |
|                                   |    Work organized via JIRA Epics and Stories (e.g. SKAO Jiraad75ab71-1245-3349-8713-12bcc32bca7cSAPP-146)                               |
+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+

--------------

🔄 Iteration and Feedback
~~~~~~~~~~~~~~~~~~~~~~~~~

We design validation activities to be **iterative**:

-  Early-stage simulations help set science and calibration requirements

-  Mid-stage validations feed into model refinement

-  Final-stage validations provide confidence before release of science results

Feedback loops with instrument teams, sky model developers, and domain scientists are key to this approach.

--------------

📌 In Practice…
~~~~~~~~~~~~~~~

   Each analysis we validate goes through a tailored process:

   -  We define the **signal of interest**

   -  Identify the relevant **nuisance models** (e.g. beam, FG, calibration)

   -  Build a suite of **simulations**

   -  Validate individual components and the pipeline as a whole

   -  Apply Bayesian model comparison and BaNTER

   -  Document performance, signal loss, and bias

This structured process ensures **science credibility is not left to chance.**

| 

🧠 5. Key Concepts
==================

Validation uses a specific vocabulary to describe how we assess the credibility of models, pipelines, and inferences. Here we define the most important concepts that underpin our methodology.

--------------

🎯 **Signal of Interest (SOI)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| The specific astrophysical signal we are trying to detect or constrain.
| In our context, this is often the **21-cm signal** from the Epoch of Reionization or Cosmic Dawn.

   Everything in the validation process is designed to ensure that our measurement of the SOI is **accurate, unbiased, and robust**.

--------------

🌌 **Composite Model**
~~~~~~~~~~~~~~~~~~~~~~

A model that describes **multiple components** in the data, such as:

-  the SOI

-  astrophysical foregrounds

-  instrumental effects

-  noise

Example:

   A 21-cm power spectrum model that includes both foreground emission and beam effects.

Composite models are required for realism -- but they can **hide biases** if components interact poorly or absorb each other’s errors.

--------------

🔎 **Predictivity vs. Accuracy**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| 

+------------------+-----------------------------------------------------------------------------+
| Term             | Definition                                                                  |
+==================+=============================================================================+
| **Predictivity** | How well a model fits the data overall (i.e. total evidence)                |
+------------------+-----------------------------------------------------------------------------+
| **Accuracy**     | Whether individual components of the model correctly describe their signals |
+------------------+-----------------------------------------------------------------------------+

..

   A model can be **predictive but not physically accurate** -- fitting the data well but getting the SOI wrong due to unmodelled systematics.

--------------

⚖️ **Bayesian Evidence and Bayes Factors**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| Bayesian evidence quantifies how well a model fits the data *on average* over its parameter space.
| The **Bayes factor** compares the evidence of two models:

-  Value >1: model A preferred

-  Value <1: model B preferred

Bayes factors are used in **Bayesian model comparison** (BFBMC), but this alone doesn’t guarantee accurate SOI recovery (see next concept).

--------------

🚫 **Failure of Bayes-Factor-Only Comparison**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bayesian model comparison can mislead if:

-  A model fits the data well **in aggregate**

-  But does so by misattributing signal between components

This is particularly dangerous when the SOI is **sub-dominant** (e.g. buried beneath foregrounds).

--------------

✅ **BaNTER (Bayesian Null Test Evidence Ratio)**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

BaNTER is a validation framework designed to detect when a model is **at risk of producing biased SOI estimates**.

It works by:

#. Running a **null test** on simulated data that contains no SOI

#. Comparing the evidence of the nuisance-only model vs. the full composite model

#. If the composite model fits the SOI-free data better, it may be **absorbing residual structure** into the SOI -- a red flag for bias

..

   BaNTER provides a **prior penalty** against risky models before they are used for inference.

--------------

🧰 **Validated Posterior Odds**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This combines:

-  **Bayes factor** (a posteriori evidence from real data)

-  **BaNTER null test** (a priori model credibility)

Result: a robust, **bias-aware model selection criterion**, improving confidence in the final inference.

--------------

**Validation Workflow**
~~~~~~~~~~~~~~~~~~~~~~~

| 

The diagram highlights three main stages -- **model specification**, **model validation**, and **data analysis** -- and distinguishes between a standard unvalidated Bayesian inference workflow (dashed red lines) and the enhanced BaNTER-validated approach (solid black lines). This formalises the process of introducing prior credibility assessments before posterior model comparison, improving robustness of signal inference. *(Figure credit:* `Sims+2025 <https://arxiv.org/abs/2502.14029>`__\ *)*

| 

--------------

These concepts form the **intellectual backbone** of our validation framework -- combining physical realism, statistical rigour, and practical insight to support trustworthy SKA science.

| 

| 

🧰 6. Tools We Use
==================

Robust validation requires powerful tools that can model, simulate, and statistically analyse SKA-class data and systems. The UKSRC-ST team leverages a suite of open-source and in-house tools, tailored to the unique challenges of 21-cm cosmology and interferometric calibration.

--------------

🖥️ **Simulation Tools**
~~~~~~~~~~~~~~~~~~~~~~~

These generate realistic data for testing pipelines, evaluating sensitivity, and injecting known signals.

+-------------+--------------------------------------------------------------------------+
| **Tool**    | **Purpose**                                                              |
+=============+==========================================================================+
| ``pyuvsim`` | High-accuracy visibility simulator based on the Measurement Equation     |
+-------------+--------------------------------------------------------------------------+
| OSKAR       | Full-featured radio telescope simulator with beam and ionosphere support |
+-------------+--------------------------------------------------------------------------+
| fftvis      | High-performance visibility simulator using non-uniform FFT (NUFFT)      |
+-------------+--------------------------------------------------------------------------+

..

   These tools allow us to simulate full datasets with known ground truth, including beams, sky models, noise, and layout.

--------------

📈 **Bayesian Inference Tools**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These are used to fit models to simulated (or real) data, and evaluate the evidence for different scientific hypotheses.

============= =========================================================
**Tool**      **Purpose**
============= =========================================================
``BayesEoR``  Bayesian inference framework for the 21-cm power spectrum
``PolyChord`` Nested sampler used for evidence computation
``BaNTER``    Framework for null-test-based model validation
============= =========================================================

These tools enable us to perform:

-  Posterior estimation

-  Model comparison

-  Validation via posterior odds

--------------

🧪 **Validation Frameworks and Perturbation Studies**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Science recovery requires knowledge of the instrument. This knowledge is necessarily incomplete (e.g. element patterns and signal chain characterised to x% and y% accuracy, with x and y < 100). Thus, the question naturally arises: is our knowledge sufficient for precision cosmology? To answer this, we can test sensitivity to systematic uncertainties by perturbing model components:

-  | **Beam FWHM perturbation framework**
   | (e.g. ``ValSKA-HERA-beam-FWHM`` GitHub repo)

-  **Instrument layout variation**

-  **Foreground modelling variations**

-  **Sky model incompleteness tests**

These are used to probe how errors in inputs propagate to science outputs -- and what level of precision is required to keep them under control.

--------------

🖧 **Infrastructure**
~~~~~~~~~~~~~~~~~~~~

| 

============ ==========================================================
**Platform** **Purpose**
============ ==========================================================
**Azimuth**  UKSRC GPU-enabled local workstation (setup for validation)
**Galahad**  UoM HPC platform (batch + interactive modes)
============ ==========================================================

We use Singularity and Docker containers for **reproducible software environments**, including custom builds for ``BayesEoR``, ``pyuvsim``, and ``PolyChord``.

--------------

🗃️ **Version Control and Collaboration**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| 

+----------------+---------------------------------------------------------------------+
| **System**     | **Use**                                                             |
+================+=====================================================================+
| **GitHub**     | Code repositories (e.g. simulations, notebooks, validation tooling) |
+----------------+---------------------------------------------------------------------+
| **JIRA**       | Epic and story tracking                                             |
+----------------+---------------------------------------------------------------------+
| **Confluence** | Documentation, meeting minutes, validation primer                   |
+----------------+---------------------------------------------------------------------+
| **Slack**      | Team and stakeholder communications                                 |
+----------------+---------------------------------------------------------------------+
| **Miro**       | Visual planning, feature mapping                                    |
+----------------+---------------------------------------------------------------------+

--------------

This toolset is **modular, extensible, and FAIR-aligned**, allowing us to scale from tightly controlled validation cases to complex, high-dimensional SKA use cases.

| 

| 

🤝 7. How Stakeholders Benefit
==============================

While the methods we use are technical, the **value of validation is strategic**. It ensures that science with the SKA and its precursors is credible, accurate, and actionable.

Here’s how validation supports different stakeholder groups:

--------------

🔬 For Science Leads and Analysts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  | **Confidence in Results**
   | Know that reported detections or upper limits are statistically sound, not artefacts of systematics.

-  | **Model Selection with Rigor**
   | Use validated posterior odds to compare competing theories or astrophysical models.

-  | **Targeted Model Refinement**
   | Identify where modelling effort is most needed (e.g. better beams vs. better sky models).

--------------

🛠️ For Instrumentation and Calibration Teams
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  | **Requirements Derivation**
   | Quantify how precisely components (e.g. beam FWHM, antenna layout) must be known to support specific science goals.

-  | **Feedback Loops**
   | Understand how instrument choices affect scientific accuracy, even before deployment.

--------------

💼 For Programme Managers and Funders
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  | **Risk Reduction**
   | Validation reduces the risk of costly reanalysis, spurious claims, or retraction of results.

-  | **Investment Prioritisation**
   | Enables data-driven decisions on where to focus calibration, simulation, or modelling efforts.

-  | **Impact Tracking**
   | Provides evidence of progress toward precision cosmology readiness -- key for reporting and review cycles.

--------------

📣 Stakeholder Benefits Summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Why This Matters to Stakeholders

-  Validation builds trust in science outputs before real data even arrives
-  It provides quantitative answers to questions like:
   “Is our beam model good enough?” or “What’s the risk of false detection?”
-  Helps prioritise which instrument parameters or modelling choices matter most
-  Makes UKSRC science contributions more credible and internationally competitive

| 

--------------

   ✅ **In short**: Validation turns “we hope this works” into “we have evidence that it does.”

| 

🔭 8. Looking Ahead
===================

Validation is not a one-off task -- it is a continuous process that evolves alongside our instruments, software, and science goals. As we scale toward full SKA operations, the UKSRC-ST team will work on ensuring that validation keeps pace with the growing complexity and ambition of the science.

--------------

📈 Scaling to SKA-Class Complexity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  | **Bigger Simulations**
   | We are expanding to simulate full SKA-class observations, with thousands of antennas and high-resolution sky models.

-  | **More Science Cases**
   | After establishing pipelines for 21-cm cosmology, we aim to extend validation to other domains such as pulsar timing, continuum imaging, and intensity mapping.

-  | **Cross-Validation Across Tools**
   | Ongoing efforts to compare outputs across multiple simulators (e.g. ``pyuvsim``, ``fftvis``, ``OSKAR``) will help identify hidden assumptions and strengthen robustness.

--------------

⚙️ Automation and Reproducibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  | **FAIR-Aligned Pipelines**
   | We’re building validation workflows that are Findable, Accessible, Interoperable, and Reproducible.

-  | **CI/CD for Science**
   | Moving toward containerized, automated validation tests that run as part of our development cycle.

-  | **Traceable Deliverables**
   | Versioned validation reports will allow stakeholders to track performance over time.

--------------

🧠 Deeper Integration with Inference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  | **Validated Posterior Odds**
   | Future analyses can directly incorporate model credibility (via BaNTER) into parameter estimation.

-  | **Uncertainty-Aware Decision Making**
   | Helping scientists and instrument teams understand not just *what* a result is, but *how reliable* it is -- and *why*.

--------------

👥 Strengthening Stakeholder Engagement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  | **Transparent Reporting**
   | We’ll continue to publish validation results, failure modes, and assumptions clearly and accessibly.

-  | **Collaborative Requirements Setting**
   | Validation outputs should inform calibration requirements, observing strategies, and data processing plans.

-  | **Training and Onboarding Support**
   | Materials and tutorials will help new team members, scientists, and partners understand and contribute to validation efforts.

--------------

   🚀 **The future of SKA science depends on getting the analysis right -- and that starts with validation.**

By investing in rigorous, scalable validation now, we’re laying the foundation for **credible, world-leading science** with SKA and its pathfinders.

| 

| 

| 

| 

| 

| 

| 

| 

| 

| 

| 
