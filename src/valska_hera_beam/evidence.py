"""
Evidence evaluation module for ValSKA-HERA-beam-FWHM project.

This module provides functions to calculate and interpret Bayes factors
between models in the BayesEoR analysis of HERA beam perturbations.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import tqdm

# import numpy as np
from anesthetic import read_chains
from bayeseor.analyze.analyze import DataContainer


def interpret_bayes_factor(log_bf):
    """Interpret the strength of evidence from log Bayes factor"""
    if log_bf > 5:
        return "Very strong evidence for model 1"
    elif log_bf > 3:
        return "Strong evidence for model 1"
    elif log_bf > 1:
        return "Moderate evidence for model 1"
    elif log_bf > -1:
        return "Weak/inconclusive evidence"
    elif log_bf > -3:
        return "Moderate evidence for model 2"
    elif log_bf > -5:
        return "Strong evidence for model 2"
    else:
        return "Very strong evidence for model 2"


def calculate_bayes_factor(
    chain_path_1,
    chain_path_2,
    model_name_1="Model 1",
    model_name_2="Model 2",
    verbose=True,
):
    """
    Calculate Bayes factor between two models given their chain directories.

    Parameters:
    -----------
    chain_path_1 : str or Path
        Path to the first model's chain directory (numerator in Bayes factor)
    chain_path_2 : str or Path
        Path to the second model's chain directory (denominator in Bayes factor)
    model_name_1 : str
        Name of the first model for display purposes
    model_name_2 : str
        Name of the second model for display purposes
    verbose : bool
        Whether to print detailed output (default: True)

    Returns:
    --------
    dict : Dictionary containing results with keys:
           - 'model_1': str (model name)
           - 'model_2': str (model name)
           - 'log_evidence_1': float or None
           - 'log_evidence_2': float or None
           - 'log_bayes_factor': float or None (ln(Z1/Z2))
           - 'interpretation': str
           - 'success': bool
           - 'error': str or None
    """

    result = {
        "model_1": model_name_1,
        "model_2": model_name_2,
        "log_evidence_1": None,
        "log_evidence_2": None,
        "log_bayes_factor": None,
        "interpretation": "Analysis failed",
        "success": False,
        "error": None,
    }

    try:
        # Load first model chain
        if verbose:
            print(f"Loading {model_name_1} chain from: {chain_path_1}")
        chain_1 = read_chains(chain_path_1)
        evidence_1 = chain_1.logZ()
        result["log_evidence_1"] = evidence_1
        if verbose:
            print(f"{model_name_1} log evidence: {evidence_1:.6f}")

        # Load second model chain
        if verbose:
            print(f"Loading {model_name_2} chain from: {chain_path_2}")
        chain_2 = read_chains(chain_path_2)
        evidence_2 = chain_2.logZ()
        result["log_evidence_2"] = evidence_2
        if verbose:
            print(f"{model_name_2} log evidence: {evidence_2:.6f}")

        # Calculate Bayes factor (ln(Z1/Z2))
        log_bayes_factor = evidence_1 - evidence_2
        result["log_bayes_factor"] = log_bayes_factor
        result["interpretation"] = interpret_bayes_factor(log_bayes_factor)
        result["success"] = True

        if verbose:
            print(
                f"Log Bayes Factor (ln({model_name_1}/{model_name_2})): {log_bayes_factor:.6f}"
            )
            print(f"Interpretation: {result['interpretation']}")

    except Exception as e:
        error_msg = f"Error calculating Bayes factor: {e}"
        result["error"] = error_msg
        if verbose:
            print(error_msg)

    return result


def analyze_bayeseor_perturbation(
    pert_level,
    dir_prefix,
    expected_ps=214777.66068216303,
    create_plots=True,
    verbose=True,
):
    """
    Analyze a specific BayesEoR perturbation level, including plots and BaNTER validation.

    Parameters:
    -----------
    pert_level : str
        Perturbation level (e.g., '-1e-3pp', '+1e0pp')
    dir_prefix : Path
        Base directory containing the chains
    expected_ps : float
        Expected power spectrum value (default: 214777.66068216303)
    create_plots : bool
        Whether to create posterior plots (default: True)
    verbose : bool
        Whether to print detailed output (default: True)

    Returns:
    --------
    dict : Dictionary containing results with keys:
           - 'perturbation': str
           - 'plot_success': bool
           - 'bayes_factor_result': dict (from calculate_bayes_factor)
           - 'validation': str ('PASS', 'FAIL', or 'ERROR')
    """

    if verbose:
        print(f"\n--- Processing BayesEoR Perturbation: {pert_level} ---")

    result = {
        "perturbation": pert_level,
        "plot_success": False,
        "bayes_factor_result": None,
        "validation": "ERROR",
    }

    # Define directory names for this perturbation level
    GSM_FgEoR_dirname = (
        f"v5d0/GSM_FgEoR_{pert_level}/MN-23-23-38-2-2.63-2.82-6.2E-03-lp-dPS-v1/"
    )
    # GSM_FgOnly_dirname = (
    #     f"v5d0/GSM_FgOnly_{pert_level}/MN-23-23-38-2-2.63-2.82-6.2E-03-lp-dPS-v1/"
    # )

    # Create posterior plot if requested
    if create_plots:
        if verbose:
            print(f"Creating posterior plot for GSM_FgEoR_{pert_level}")
        try:
            data = DataContainer(
                [GSM_FgEoR_dirname],
                dir_prefix=dir_prefix,
                expected_ps=expected_ps,
                labels=[f"GSM_FgEoR_{pert_level}"],
            )

            fig = data.plot_power_spectra_and_posteriors(
                suptitle=f"GSM FgEoR Analysis - {pert_level}",
                plot_fracdiff=True,
                plot_priors=True,
            )

            assert fig is not None, "Plot generation failed"

            plt.show()
            result["plot_success"] = True

        except Exception as e:
            if verbose:
                print(f"Error creating plot for GSM_FgEoR_{pert_level}: {e}")
            return result
    else:
        result["plot_success"] = True

    # Calculate Bayes factor using generalized function
    if verbose:
        print(f"--- Bayes Factor Calculation for {pert_level} ---")

    # Construct full paths
    fgeor_path = (
        dir_prefix
        / f"v5d0/GSM_FgEoR_{pert_level}/MN-23-23-38-2-2.63-2.82-6.2E-03-lp-dPS-v1/data-"
    )
    fgonly_path = (
        dir_prefix
        / f"v5d0/GSM_FgOnly_{pert_level}/MN-23-23-38-2-2.63-2.82-6.2E-03-lp-dPS-v1/data-"
    )

    bf_result = calculate_bayes_factor(
        chain_path_1=fgeor_path,
        chain_path_2=fgonly_path,
        model_name_1=f"GSM_FgEoR_{pert_level}",
        model_name_2=f"GSM_FgOnly_{pert_level}",
        verbose=verbose,
    )

    result["bayes_factor_result"] = bf_result

    if bf_result["success"]:
        log_bayes_factor = bf_result["log_bayes_factor"]

        # BaNTER validation result
        result["validation"] = "PASS" if log_bayes_factor < 0 else "FAIL"
        if verbose:
            if log_bayes_factor < 0:
                print("✅ PASS: BaNTER correctly favors foreground-only model")
            else:
                print(
                    "❌ FAIL: BaNTER incorrectly detects EoR signal in foreground-only data"
                )
    else:
        result["validation"] = "ERROR"

    return result


def get_available_perturbations(paths_dict=None):
    """
    Extract all available perturbation levels from paths dictionary.

    Parameters:
    -----------
    paths_dict : dict, optional
        Dictionary of paths from utils.load_paths(). If None, loads paths automatically.

    Returns:
    --------
    tuple : (all_perturbations, negative_perturbations, positive_perturbations)
        Lists of perturbation level strings
    """
    from .utils import load_paths

    # Load paths if not provided
    if paths_dict is None:
        paths_dict = load_paths()

    # Extract perturbation levels from GSM_FgEoR keys
    perturbations = []
    for key in paths_dict.keys():
        if key.startswith("GSM_FgEoR_"):
            # Extract the perturbation part (e.g., "-1e-3pp")
            perturbation = key.replace("GSM_FgEoR_", "")

            # Only add if corresponding FgOnly path exists
            if f"GSM_FgOnly_{perturbation}" in paths_dict:
                perturbations.append(perturbation)

    # Sort and separate negative and positive perturbations
    negative_perts = [p for p in perturbations if p.startswith("-")]
    positive_perts = [p for p in perturbations if p.startswith("+")]

    # Sort by magnitude
    def sort_by_magnitude(pert_list):
        def get_magnitude(p):
            # Extract the numerical part between the sign and "pp"
            num_part = p[1:-2]  # Remove sign and "pp"
            try:
                if "e" in num_part:
                    base, exp = num_part.split("e")
                    return float(base) * (10 ** float(exp))
                else:
                    return float(num_part)
            except ValueError:
                return 0

        return sorted(pert_list, key=lambda p: get_magnitude(p))

    negative_perts = sort_by_magnitude(negative_perts)
    positive_perts = sort_by_magnitude(positive_perts)

    # Combine all perturbations in a sensible order (negative then positive)
    all_perts = negative_perts + positive_perts

    return all_perts, negative_perts, positive_perts


def run_complete_bayeseor_analysis(
    perturbation_levels=None,
    dir_prefix=None,
    paths_dict=None,
    expected_ps=214777.66068216303,
    create_plots=False,
    show_detailed_results=False,
    verbose=True,
    show_progress=True,
    only_negative=False,
    only_positive=False,
):
    """
    Run complete BayesEoR perturbation analysis with customizable output.

    Parameters:
    -----------
    perturbation_levels : list, optional
        List of perturbation levels to analyze. If None, uses default set.
    dir_prefix : Path, optional
        Base directory containing the chains. If None, uses default path.
    paths_dict : dict, optional
        Dictionary of paths from utils.load_paths(). If None, loads paths automatically.
     expected_ps : float
        Expected power spectrum value (default: 214777.66068216303)
    create_plots : bool
        Whether to create posterior plots for each perturbation (default: False)
    show_detailed_results : bool
        Whether to show detailed results section (default: False)
    verbose : bool
        Whether to print detailed output during processing (default: True)
    show_progress : bool
        Whether to show a progress bar during analysis (default: True)
    only_negative : bool, optional
        If True, only analyzes negative perturbations (default: False)
    only_positive : bool, optional
        If True, only analyzes positive perturbations (default: False)

    Returns:
    --------
    dict : Dictionary containing:
           - 'results': list of individual analysis results
           - 'summary': dict with pass/fail/error counts
           - 'successful_results': list of successfully analyzed perturbations
    """

    # # Set default perturbation levels if not provided
    # if perturbation_levels is None:
    #     perturbation_levels = [
    #         "-1e-3pp",
    #         "-1e-2pp",
    #         "-1e-1pp",
    #         "-1e0pp",
    #         "-1e1pp",  # Negative perturbations
    #         "-2e0pp",
    #         "-5e0pp",  # More negative perturbations
    #         "+1e-3pp",
    #         "+1e-2pp",
    #         "+1e-1pp",
    #         "+1e0pp",
    #         "+1e1pp",  # Positive perturbations
    #     ]

    # Set perturbation levels if not provided
    if perturbation_levels is None:
        all_perts, negative_perts, positive_perts = get_available_perturbations(
            paths_dict
        )

        # Select perturbations based on flags
        if only_negative:
            perturbation_levels = negative_perts
        elif only_positive:
            perturbation_levels = positive_perts
        else:
            perturbation_levels = all_perts

    # Set default directory if not provided
    if dir_prefix is None:
        cwd = Path("/home/psims/share/test/BayesEoR/notebooks/")
        dir_prefix = cwd / Path("../chains/")

    if verbose:
        print("=== Complete BayesEoR Analysis ===")
        print(f"Analyzing {len(perturbation_levels)} perturbation levels...")
        print("Perturbation levels:", perturbation_levels)
        if create_plots:
            print("Note: Plots will be generated for each perturbation")

        # Analyze all perturbations
        all_results = []

        # Set up progress tracking
        if show_progress and verbose and len(perturbation_levels) > 1:
            try:
                from tqdm import tqdm

                # Create a progress bar with descriptive format
                perturbation_iterator = tqdm(
                    perturbation_levels,
                    desc="Analyzing perturbations",
                    unit="case",
                    ncols=80,  # Width of the progress bar
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                )
            except ImportError:
                # Fallback if tqdm is not installed
                print("Note: Install 'tqdm' for progress bar display")
                perturbation_iterator = perturbation_levels
        else:
            # No progress bar
            perturbation_iterator = perturbation_levels

        # Process each perturbation with progress tracking
        for i, pert_level in enumerate(perturbation_iterator, 1):
            if verbose and not show_progress:
                # Only show this if we're not using a progress bar
                print(
                    f"\n--- Processing {i}/{len(perturbation_levels)}: {pert_level} ---"
                )

            result = analyze_bayeseor_perturbation(
                pert_level=pert_level,
                dir_prefix=dir_prefix,
                expected_ps=expected_ps,
                create_plots=create_plots,
                verbose=False
                if show_progress
                else verbose,  # Reduce verbosity when using progress bar
            )
            all_results.append(result)

            # Update progress bar description with current perturbation level
            if show_progress and hasattr(perturbation_iterator, "set_description"):
                perturbation_iterator.set_description(f"Analyzing: {pert_level}")

    # Generate summary table (always shown)
    print("\n" + "=" * 80)
    print("COMPLETE BAYESEOR PERTURBATION ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"{'Perturbation':<12} {'Log BF':<10} {'Validation':<12} {'Interpretation'}")
    print("-" * 80)
    # print("-" * 85)  # Slightly longer line for wider validation column

    pass_count = 0
    fail_count = 0
    error_count = 0

    for result in all_results:
        pert = result["perturbation"]
        validation = result["validation"]

        if validation == "ERROR":
            print(f"{pert:<12} {'ERROR':<10} {'❌ ERROR':<15} {'Analysis failed'}")
            error_count += 1
        else:
            bf_result = result["bayes_factor_result"]
            if bf_result and bf_result["success"]:
                log_bf = bf_result["log_bayes_factor"]
                interpretation = bf_result["interpretation"]

                # Add tick or cross based on validation result
                if validation == "PASS":
                    validation_display = "✅ PASS"
                    pass_count += 1
                else:  # FAIL
                    validation_display = "❌ FAIL"
                    fail_count += 1

                print(
                    f"{pert:<12} {log_bf:<10.3f} {validation_display:<15} {interpretation}"
                )
            else:
                print(f"{pert:<12} {'N/A':<10} {'❌ ERROR':<15} {'Calculation failed'}")
                error_count += 1

    print("-" * 80)
    print(
        f"TOTAL: {len(all_results)} cases | PASS: {pass_count} | FAIL: {fail_count} | ERROR: {error_count}"
    )

    if pass_count == len(all_results) - error_count:
        print("🎉 ALL VALID CASES PASSED BaNTER VALIDATION!")
    elif fail_count > 0:
        print("⚠️  SOME CASES FAILED BaNTER VALIDATION - Investigation needed")

    print(
        f"\nBaNTER Validation Complete - Processed {len(perturbation_levels)} perturbation levels"
    )

    # Prepare successful results for detailed output and return
    successful_results = []
    for result in all_results:
        if result["validation"] != "ERROR" and result["bayes_factor_result"]["success"]:
            bf_data = result["bayes_factor_result"]
            detailed_result = {
                "perturbation": result["perturbation"],
                "log_evidence_fgeor": bf_data["log_evidence_1"],
                "log_evidence_fgonly": bf_data["log_evidence_2"],
                "log_bayes_factor": bf_data["log_bayes_factor"],
                "validation": result["validation"],
                "interpretation": bf_data["interpretation"],
            }
            successful_results.append(detailed_result)

    # Show detailed results if requested
    if show_detailed_results:
        print("\n" + "=" * 60)
        print("DETAILED RESULTS FOR FURTHER ANALYSIS")
        print("=" * 60)

        for detailed_result in successful_results:
            print(f"Perturbation: {detailed_result['perturbation']}")
            print(f"  FgEoR Evidence: {detailed_result['log_evidence_fgeor']:.6f}")
            print(f"  FgOnly Evidence: {detailed_result['log_evidence_fgonly']:.6f}")
            print(f"  Log Bayes Factor: {detailed_result['log_bayes_factor']:.6f}")
            print(f"  Validation: {detailed_result['validation']}")
            print(f"  Interpretation: {detailed_result['interpretation']}")
            print()

        print(
            f"Successfully analyzed {len(successful_results)} out of {len(perturbation_levels)} perturbations"
        )

    # Return structured results
    return {
        "results": all_results,
        "summary": {
            "total": len(all_results),
            "pass": pass_count,
            "fail": fail_count,
            "error": error_count,
        },
        "successful_results": successful_results,
    }


# =============================================================================
# EXAMPLES
# =============================================================================

run_run_examples = False

if run_run_examples:
    # Example 1: Calculate single Bayes factor between two directories
    print("=== Example 1: Single Bayes Factor Calculation ===")

    # Setup paths
    cwd = Path("/home/psims/share/test/BayesEoR/notebooks/")
    dir_prefix = cwd / Path("../chains/")

    # Define two chain directories
    chain_1 = (
        dir_prefix
        / "v5d0/GSM_FgEoR_-1e-3pp/MN-23-23-38-2-2.63-2.82-6.2E-03-lp-dPS-v1/data-"
    )
    chain_2 = (
        dir_prefix
        / "v5d0/GSM_FgOnly_-1e-3pp/MN-23-23-38-2-2.63-2.82-6.2E-03-lp-dPS-v1/data-"
    )

    bf_result = calculate_bayes_factor(
        chain_path_1=chain_1,
        chain_path_2=chain_2,
        model_name_1="GSM_FgEoR_-1e-3pp",
        model_name_2="GSM_FgOnly_-1e-3pp",
        verbose=True,
    )

    print("\nResults:")
    print(f"Success: {bf_result['success']}")
    if bf_result["success"]:
        print(f"Log Bayes Factor: {bf_result['log_bayes_factor']:.6f}")
        print(f"Interpretation: {bf_result['interpretation']}")
    else:
        print(f"Error: {bf_result['error']}")

    print("\n" + "=" * 80 + "\n")

    # Example 2: Quick summary analysis (default)
    print("=== Example 2: Quick Summary Analysis ===")
    results = run_complete_bayeseor_analysis()

    print("\n" + "=" * 80 + "\n")

    # Example 3: Analysis with plots (uncomment to run)
    print("=== Example 3: Analysis with Plots ===")
    results_with_plots = run_complete_bayeseor_analysis(create_plots=True)

    # Example 4: Analysis with detailed results
    print("=== Example 4: Analysis with Detailed Results ===")
    results_detailed = run_complete_bayeseor_analysis(show_detailed_results=True)

    print("\n" + "=" * 80 + "\n")

    # Example 5: Custom perturbation subset
    print("=== Example 5: Custom Perturbation Subset ===")
    custom_perturbations = ["-1e-3pp", "-1e-2pp", "+1e-3pp"]
    results_custom = run_complete_bayeseor_analysis(
        perturbation_levels=custom_perturbations, show_detailed_results=True
    )

    print("\n" + "=" * 80 + "\n")

    # Example 6: Programmatic access to results
    print("=== Example 6: Programmatic Access to Results ===")
    print(f"Total PASS cases: {results['summary']['pass']}")
    print(f"Total FAIL cases: {results['summary']['fail']}")
    print(f"Total ERROR cases: {results['summary']['error']}")

    # Find any failed cases
    failed_cases = [
        r for r in results["successful_results"] if r["validation"] == "FAIL"
    ]
    if failed_cases:
        print(f"\nFailed cases ({len(failed_cases)}):")
        for case in failed_cases:
            print(f"  {case['perturbation']}: BF = {case['log_bayes_factor']:.3f}")
    else:
        print("\nNo failed cases found!")
