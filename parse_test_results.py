import xml.etree.ElementTree as ET
import json
import os
import sys
from datetime import datetime

def parse_xml_files(test_result_dir, test_type):
    suite_results = []
    case_results = []

    if not os.path.exists(test_result_dir):
        print(f"Test result directory {test_result_dir} does not exist.")
        return suite_results, case_results

    for root_dir, _, files in os.walk(test_result_dir):
        for filename in files:
            if filename.endswith('.xml') and filename.startswith('TEST-'):
                file_path = os.path.join(root_dir, filename)
                tree = ET.parse(file_path)
                root = tree.getroot()

                # Determine if root is 'testsuite' or 'testsuites'
                if root.tag == 'testsuite':
                    # Process the single testsuite
                    testsuite = root
                    suite_result, case_result = parse_testsuite(testsuite, test_type)
                    if suite_result:
                        suite_results.append(suite_result)
                    if case_result:
                        case_results.extend(case_result)
                elif root.tag == 'testsuites':
                    # Process multiple testsuites
                    for testsuite in root.findall('testsuite'):
                        suite_result, case_result = parse_testsuite(testsuite, test_type)
                        if suite_result:
                            suite_results.append(suite_result)
                        if case_result:
                            case_results.extend(case_result)
    return suite_results, case_results

def parse_testsuite(testsuite, test_type):
    try:
        # Suite-level data
        tests = int(testsuite.get('tests', 0))
        failures = int(testsuite.get('failures', 0))
        errors = int(testsuite.get('errors', 0))
        skipped = int(testsuite.get('skipped', 0))
        time = float(testsuite.get('time', 0))
        timestamp = testsuite.get('timestamp', datetime.now().isoformat())

        passed = tests - failures - errors - skipped
        status = 'passed' if failures == 0 and errors == 0 else 'failed'

        suite_result = {
            'timestamp': timestamp,
            'tests': tests,
            'passed': passed,
            'failures': failures,
            'errors': errors,
            'skipped': skipped,
            'time': time,
            'status': status,
            'suite_name': testsuite.get('name', 'Unknown'),
            'type': test_type
        }

        # Collect test case results
        case_results = []
        for testcase in testsuite.findall('testcase'):
            case_name = testcase.get('name')
            classname = testcase.get('classname')
            case_time = float(testcase.get('time', 0))
            case_status = 'passed'
            failure_message = ''
            failure_type = ''

            # Check for failures or errors
            failure = testcase.find('failure')
            error = testcase.find('error')
            skipped_element = testcase.find('skipped')

            if failure is not None:
                case_status = 'failed'
                failure_message = failure.text or ''
                failure_type = failure.get('type', '')
            elif error is not None:
                case_status = 'error'
                failure_message = error.text or ''
                failure_type = error.get('type', '')
            elif skipped_element is not None:
                case_status = 'skipped'

            case_results.append({
                'timestamp': timestamp,
                'suite_name': testsuite.get('name'),
                'test_name': case_name,
                'classname': classname,
                'status': case_status,
                'time': case_time,
                'failure_type': failure_type,
                'failure_message': failure_message,
                'type': test_type
            })

        return suite_result, case_results
    except Exception as e:
        print(f"Error parsing testsuite: {e}")
        return None, None

def update_data_file(suite_results, case_results, data_file_path):
    data = {'suites': [], 'cases': []}
    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, 'r') as f:
                existing_data = json.load(f)
                data['suites'] = existing_data.get('suites', [])
                data['cases'] = existing_data.get('cases', [])
        except json.JSONDecodeError as e:
            print(f"Error loading JSON from {data_file_path}: {e}")
            print("Proceeding with empty data.")
        except Exception as e:
            print(f"Unexpected error reading {data_file_path}: {e}")
            print("Proceeding with empty data.")

    data['suites'].extend(suite_results)
    data['cases'].extend(case_results)

    # Optionally limit the size of data
    MAX_ENTRIES = 1000
    data['suites'] = data['suites'][-MAX_ENTRIES:]
    data['cases'] = data['cases'][-MAX_ENTRIES * 10:]

    with open(data_file_path, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python parse_test_results.py <test_result_dir> <test_type> <output_json_path>")
        sys.exit(1)

    test_result_dir = sys.argv[1]
    test_type = sys.argv[2]
    data_file_path = sys.argv[3]
    suite_results, case_results = parse_xml_files(test_result_dir, test_type)
    update_data_file(suite_results, case_results, data_file_path)
