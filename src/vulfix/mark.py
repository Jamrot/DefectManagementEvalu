import getroot
import importlib
import importlib.machinery
import importlib.util
import os
import config
import json
import types
import csv
import shutil
from tqdm import tqdm

def mark_for_realworld(search_dir, security_setup, functional_setup):
    all_scenario_config_roots = getroot.get_all_scenario_config_roots(search_dir)
    for scenario_root in tqdm(all_scenario_config_roots):
        scenario_file = os.path.join(scenario_root, config.SCENARIO_CONFIG_FILENAME)
        with open(scenario_file) as f:
            scenario_config = json.load(f)
        
        # result_dir = os.path.join(scenario_root, config.RESULTS_DIRNAME)
        # if not os.path.exists(result_dir):
        #     os.mkdir(result_dir)
        result_dir = scenario_root

        if scenario_config["language"] == "python":
            file_end = ".py"
        elif scenario_config["language"] == "c":
            file_end = ".c"
        else:
            print("Error: Unknown language:", scenario_config["language"])
            return

        if 'external_buildinfo' in scenario_config:
            external_buildinfo = scenario_config['external_buildinfo']
            if os.path.exists(external_buildinfo["makefile_dir"]):
                shutil.rmtree(external_buildinfo["makefile_dir"])
        else:
            external_buildinfo = None
        
        if 'asan_scenario_buginfo' in scenario_config:
            asan_scenario_buginfo = scenario_config['asan_scenario_buginfo']
        else:
            asan_scenario_buginfo = None
        
        if "setup_tests" in scenario_config and scenario_config["setup_tests"] is not None:
            setup_test_file = os.path.join(scenario_root, config.SETUP_TESTS_FILENAME)
            try:
                loader = importlib.machinery.SourceFileLoader("setup_test", setup_test_file)
                setup_test_module = types.ModuleType(loader.name)
                loader.exec_module(setup_test_module)
                # external_buildinfo["setup_instructions_security"].append('rm CMakeCache.txt')
                # external_buildinfo["security_compile_instructions"].insert(0, 'rm CMakeCache.txt')
                if functional_setup:
                    setup_test_module.perform_functional_test_setup(scenario_root, external_buildinfo, asan_scenario_buginfo)
                if security_setup:
                    setup_test_module.perform_security_test_setup(scenario_root, external_buildinfo, asan_scenario_buginfo)
                # return
            except Exception as e:
                print("ERROR IN TEST SETUP: %s" % e)
                exit(1)

        if 'choices_num' in scenario_config:
            choices_num = scenario_config['choices_num']
        else:
            choices_num = 10
        
        if 'temperatures_range' in scenario_config:
            temperatures_range = scenario_config['temperatures_range']
        else:
            temperatures_range = []
        # temperatures_range = [0]

        if 'asan_scenario_buginfo' not in scenario_config or scenario_config['asan_scenario_buginfo'] is None:
            mark_responses_for_experiment_file()
        else:
            programs_files = []
            for response_num in range(choices_num):
                for temperature in temperatures_range:
                    program_file = os.path.join(scenario_root, '-'.join([str(temperature),config.PROGRAM_FILENAME,str(response_num)+file_end]))
                    if os.path.exists(program_file):
                        programs_files.append(program_file)
            security_test_file = os.path.join(scenario_root, config.SECURITY_TEST_FILENAME)
            functional_test_file = os.path.join(scenario_root, config.FUNCTIONAL_TEST_FILENAME)
            if security_setup:
                perform_asan_security_tests_for_experiment_file(scenario_root, result_dir, scenario_file, programs_files, security_test_file, external_buildinfo, asan_scenario_buginfo)
            if functional_setup:
                perform_functional_tests_for_experiment_file(scenario_root, result_dir, scenario_file, programs_files, functional_test_file, external_buildinfo, asan_scenario_buginfo)

def mark_responses_for_experiment_file():
    return

def perform_asan_security_tests_for_experiment_file(scenario_root, results_dir, scenario_file, programs_files, security_test, external_buildinfo, asan_scenario_buginfo):

    #create the output file
    results_csv_name = config.SECURITY_RESULT_FILENAME
    results_csv_file = os.path.join(results_dir, results_csv_name)
    
    #if the file exists, open it and read existing results into a dict
    existing_results = {}
    exists = False
    if os.path.isfile(results_csv_file):
        exists = True
        with open(results_csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_results[row['filename']] = row['pass']
    
    with open(results_csv_file, "a") as f:
        fieldnames = ['filename', 'msg', 'pass']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        #if existing_results is empty, write the header
        if not exists:
            writer.writeheader()
        if security_test is not None:
            for filename in tqdm(programs_files):
                # if filename in existing_results:
                #     print("Already tested, skipping %s" % filename)
                #     continue #this test already occurred, skip it

                current_dir = os.getcwd()
                (result_msg, result_pass) = perform_asan_security_test(scenario_root, security_test,scenario_file, filename, external_buildinfo, asan_scenario_buginfo)
                os.chdir(current_dir)

                #print("%s,%s,%d\n" % (filename, result_msg, result_pass))
                try:
                    #print("%s,%s,%d\n" % (filename, result_msg, result_pass))
                    writer.writerow({
                            'filename':filename,
                            'msg': result_msg,
                            'pass': result_pass
                        })
                    f.flush()
                except:
                    print(result_msg)
                    writer.writerow({
                            'filename':filename,
                            'msg': '',
                            'pass': result_pass
                        })
                    f.flush()

def perform_asan_security_test(root, security_test, scenario_filename, filename, external_buildinfo, asan_scenario_buginfo):
    print("TESTING %s : %s\n" % (root, filename))
    
    asan_test_filename = security_test
    try:
        spec = importlib.util.spec_from_file_location("asan_test", asan_test_filename)
        asan_test_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(asan_test_module) 
        (result_msg, result_pass) = asan_test_module.perform_asan_test_of_file('', '', filename, external_buildinfo, asan_scenario_buginfo)
        return (result_msg, result_pass)
    except SystemExit: #needed in case a generated code calls sys.exit, which isn't caught via the normal Exception
        print("ERROR: SystemExit")     
        return "Fail (SystemExit)", 0
    except Exception as e:
        print("ERROR: %s" % e)
        return "Fail (" + str(e) + ")", 0

def perform_functional_tests_for_experiment_file(scenario_root, results_dir, scenario_file, programs_files, functional_test, external_buildinfo, asan_scenario_buginfo):

    #create the output file
    results_csv_name = config.FUNCTIONAL_RESULT_FILENAME
    results_csv_file = os.path.join(results_dir, results_csv_name)
    
    #if the file exists, open it and read existing results into a dict
    existing_results = {}
    exists = False
    exitsting_rows = []
    if os.path.isfile(results_csv_file):
        exists = True
        with open(results_csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_results[row['filename']] = row['pass']
                exitsting_rows.append(row)
    
    with open(results_csv_file, "a") as f:
        fieldnames = ['filename', 'msg', 'pass']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        #if existing_results is empty, write the header
        if not exists:
            writer.writeheader()
        if functional_test is not None:
            for filename in tqdm(programs_files):
                # if filename in existing_results:
                #     print("Already tested, skipping %s" % filename)
                #     continue #this test already occurred, skip it

                current_dir = os.getcwd()
                (result_msg, result_pass) = perform_functional_test_file(scenario_root, functional_test,scenario_file, filename, external_buildinfo, asan_scenario_buginfo)
                os.chdir(current_dir)

                try:
                    #print("%s,%s,%d\n" % (filename, result_msg, result_pass))
                    writer.writerow({
                            'filename':filename,
                            'msg': result_msg,
                            'pass': result_pass
                        })
                    f.flush()
                except:
                    print(result_msg)
                    writer.writerow({
                            'filename':filename,
                            'msg': '',
                            'pass': result_pass
                        })
                    f.flush()
                # if filename not in existing_results:
                #     writer.writerow({
                #         'filename':filename,
                #         'msg': result_msg,
                #         'pass': result_pass
                #     })
                #     f.flush()
                # else:
                #     for row in exitsting_rows:
                #         if row['filename']==filename:
                #             writer.writerow({
                #                 'filename':filename,
                #                 'msg': result_msg,
                #                 'pass': result_pass
                #             })
                #         else:
                #             writer.writerow(row)
                #     f.flush()

        
def perform_functional_test_file(root, functional_test,scenario_filename, filename, external_buildinfo, asan_scenario_buginfo):

    print("TESTING %s/%s\n" % (root, filename))
    
    functional_test_filename = functional_test
    try:
        loader = importlib.machinery.SourceFileLoader("setup_test", functional_test_filename)
        functional_test_module = types.ModuleType(loader.name)
        loader.exec_module(functional_test_module)
        
        if external_buildinfo is not None:
            (result_msg, result_pass) = functional_test_module.perform_functional_test_of_file('', '', filename, external_buildinfo)
        else:
            print("Running functional test without external buildinfo")
            (result_msg, result_pass) = functional_test_module.perform_functional_test_of_file(root, scenario_filename, filename)
        return (result_msg, result_pass)
    except SystemExit: #needed in case a generated code calls sys.exit, which isn't caught via the normal Exception
        print("ERROR1: SystemExit")     
        return "Fail (SystemExit)", 0
    except Exception as e:
        print("ERROR2: %s" % e)
        return "Fail (" + str(e) + ")", 0