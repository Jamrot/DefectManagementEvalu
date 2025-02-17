import os
import config
import json
import subprocess
import getroot

def do_collect_program(save_root, response_dir):
    response_files = []
    for root, _, fs in os.walk(response_dir):
        for file in fs:
            if file.endswith('.json'):
                response_file = os.path.join(root, file)
                response_files.append(response_file)

    for response_file in response_files:
        with open(response_file) as f:
            response_data = json.load(f)
        for _, dirs, _ in os.walk(save_root):
            for item in response_data:
                response_id = item['id']
                for dir in dirs:
                    if dir in response_id:
                        save_dir = os.path.join(save_root, dir)
                        scenario_file = os.path.join(save_dir, config.SCENARIO_CONFIG_FILENAME)
                        with open(scenario_file) as f:
                            scenario_config = json.load(f)
                        language = scenario_config['language']
                        if language=='python':
                            file_end = '.py'
                        elif language=='c':
                            file_end = '.c'
                        
                        choices = item['response']['choices']
                        choices_num = len(choices)
                        temperature = item['prompt']['temperature']
                        scenario_config['choices_num'] = choices_num
                        for response_num in range(choices_num):
                            response = item['response']['choices'][response_num]['message']['content']
                            response_file = os.path.join(save_dir, '-'.join([str(temperature),config.RESPONSE_FILENAME,str(response_num)+file_end]))
                            with open(response_file, 'w') as f:
                                f.write(response)
                    
def combine_response_with_existing(search_dir):
    all_scenario_config_roots = getroot.get_all_scenario_config_roots(search_dir)
    for scenario_root in all_scenario_config_roots:
        scenario_path = os.path.join(scenario_root, config.SCENARIO_CONFIG_FILENAME)
        with open(scenario_path) as f:
            scenario_config = json.load(f)
        if 'prompt_name' in scenario_config:
            experiment_prompt_name = scenario_config['prompt_name']
        else:
            experiment_prompt_name = None
        
        if 'language' in scenario_config:
            language = scenario_config['language']
        else:
            language = None
        if language=='python':
            file_end = '.py'   
            comment_key = "#"                 
        elif language=='c':
            file_end = '.c'
            comment_key = "//"
        else:
            file_end = ''

        include_first_token = False
        if experiment_prompt_name is not None:
            if 'asan-line2line-oracle-nomessage' == experiment_prompt_name or \
                'asan-line2line-oracle-nomessage-assymetric' == experiment_prompt_name:
                include_first_token = True
        
        if 'asan_scenario_buginfo' in scenario_config:
            asan_scenario_buginfo = scenario_config['asan_scenario_buginfo']
        else:
            asan_scenario_buginfo = None
        
        if asan_scenario_buginfo is not None:
            if "addition_only" not in asan_scenario_buginfo["real_patchinfo"][0]:
                asan_scenario_buginfo["real_patchinfo"][0]["addition_only"] = False
            
            if "asan-line2line-oracle" in experiment_prompt_name:
                cut_line_start = min(asan_scenario_buginfo["real_patchinfo"][0]["edit_lines"])
                cut_line_end = max(asan_scenario_buginfo["real_patchinfo"][0]["edit_lines"])
                addition_only = asan_scenario_buginfo["real_patchinfo"][0]["addition_only"]

            # load the contents of original file
            original_file = os.path.join(scenario_root, config.ORIGINAL_FILENAME+file_end)
            if not os.path.exists(original_file):
                print("Could not find the original file for ASAN bug info")
                return
            with open(original_file, "r") as f:
                contents = f.read()
                append_contents = ""
            
            # load response
            if 'choices_num' in scenario_config:
                choices_num = scenario_config['choices_num']
            else:
                choices_num = 10
            
            if 'temperatures_range' in scenario_config:
                temperatures_range = scenario_config['temperatures_range']
            else:
                temperatures_range = []
            # print('temperature range: {}'.format(temperatures_range))
            # temperatures_range = [0.25]
            
            for response_num in range(choices_num):
                for temperature in temperatures_range:
                    response_path = os.path.join(scenario_root, '-'.join([str(temperature),config.RESPONSE_FILENAME,str(response_num)+file_end]))
                    if os.path.exists(response_path):
                        with open(response_path) as f:
                            response = f.read()
                        try:
                            new_contents = asan_combine_generated_code_with_existing(comment_key, contents, cut_line_start, cut_line_end, response, include_first_token, addition_only)
                            program_path = os.path.join(scenario_root, '-'.join([str(temperature),config.PROGRAM_FILENAME,str(response_num)+file_end]))
                            with open(program_path, 'w') as f:
                                f.write(new_contents)
                        except Exception as e:
                            new_contents = None
                            print("Error in extrapolation:" + str(e))
                            extrapolate_error = True
        else:
            new_contents = basic_combine_generated_code_with_existing(comment_key, contents, append_contents, response)
            program_path = os.path.join(scenario_root, '-'.join([str(temperature),config.PROGRAM_FILENAME,str(response_num)+file_end]))
            with open(program_path, 'w') as f:
                f.write(new_contents)

def basic_combine_generated_code_with_existing(comment_key, contents, append_contents, generated_text):
    new_contents = contents + generated_text + "\n" + append_contents
    return new_contents  

def asan_combine_generated_code_with_existing(comment_key, contents, cut_line_start, cut_line_end, generated_text, include_first_token, addition_only):
    program_lines = contents.split("\n")
    prepend_program = "\n".join(program_lines[:cut_line_start-1])
    
    # if generate_mean_logprob_comments and mean_logprob is not None:
    #     prepend_program += "\n" + comment_key + "LM generated repair code follows. mean_logprob: " + mean_logprob + "\n"
    
    if include_first_token:
        word = program_lines[cut_line_start-1].strip().split(' ')[0]
        prepend_program += "\n" + word
    if not addition_only:
        append_program = "\n".join(program_lines[cut_line_end+1:])
    else:
        append_program = "\n".join(program_lines[cut_line_end:])
    
    # gpt-3.5-few-shot
    cutoff_gen_index = generated_text.find("```")
    if not cutoff_gen_index==-1:
        generated_text = generated_text[cutoff_gen_index+len("```"):]
    prepend_match = False # for gpt-3.5-turbo
    for i in range(-30, -4):
        if len(prepend_program) > 30-i:
            cutoff_gen = prepend_program[i:].strip()
        else:
            cutoff_gen = prepend_program.strip()

        #print("cutoff_gen is ", cutoff_gen)

        if len(cutoff_gen) > 0:
            #find where cutoff_gen is in the generated text
            cutoff_gen_index = generated_text.rfind(cutoff_gen)
            if cutoff_gen_index == -1:
                continue
            else:
                #cut the generated text at the cutoff_gen
                prepend_match = True
                generated_text = generated_text[cutoff_gen_index-i:]
                break

    #get the first few words of the append program
    matched = False
    for i in range(5): # new combine
        # if len(append_program) > 30-i:
        #     cutoff_gen = append_program.strip()[:30-i].strip()
        # else:
        #     cutoff_gen = append_program.strip()

        cutoff_gen = append_program.split('\n')[i].strip()

        #print("cutoff_gen is ", cutoff_gen)

        if len(cutoff_gen) > 0:
            #find where cutoff_gen is in the generated text
            cutoff_gen_index = generated_text.rfind(cutoff_gen)
            if cutoff_gen_index == -1:
                if matched:
                    generated_text = generated_text[:cutoff_gen_matched_index]
                    append_program = "\n".join(program_lines[cut_line_end+i:])
                    break
                else:
                    continue
            else:
                #cut the generated text at the cutoff_gen
                matched = True
                cutoff_gen_matched = cutoff_gen
                cutoff_gen_matched_index = cutoff_gen_index
                if i==4:
                    generated_text = generated_text[:cutoff_gen_index]
                    append_program = "\n".join(program_lines[cut_line_end+i:])
                # break
    
    if not matched: # original combine
        for i in range(4, 30):
            if len(append_program) > 30-i:
                cutoff_gen = append_program[:30-i].strip()
            else:
                cutoff_gen = append_program.strip()

            #print("cutoff_gen is ", cutoff_gen)

            if len(cutoff_gen) > 0:
                #find where cutoff_gen is in the generated text
                cutoff_gen_index = generated_text.rfind(cutoff_gen)
                if cutoff_gen_index == -1:
                    continue
                else:
                    #cut the generated text at the cutoff_gen
                    matched = True
                    generated_text = generated_text[:cutoff_gen_index]
                    break

    if not matched:
        #take everything up to the last newline character (don't take a partial line)
        generated_text = generated_text.rsplit('\n', 1)[0]

        #problem, couldn't find the cutoff_gen in the generated text
        #raise Exception("Couldn't find the cutoff_gen in the generated text")
    
    new_contents = prepend_program + generated_text + append_program
    
    return new_contents