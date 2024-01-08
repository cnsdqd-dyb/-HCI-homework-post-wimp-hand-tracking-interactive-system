import concurrent.futures
import logging
import os
import time

import openai
from openai import OpenAI
from  chat_model.abstract_language_model import AbstractLanguageModel
from chat_model.tot import *
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class TotType:
    TreeofThoughtsASearch = "TreeofThoughtsASearch"
    TreeofThoughtsBFS = "TreeofThoughts"
    TreeofThoughtsDFS = "TreeofThoughtsAStar"
    TreeofThoughtsMonteCarlo = "TreeofThoughtsMonteCarlo"
    TreeofThoughtsBEST = "TreeofThoughtsMonteCarloUCT"

class OpenAILanguageModel(AbstractLanguageModel):
    def __init__(
        self,
        api_key="",
        strategy="cot",
        evaluation_strategy="value",
        api_base="",
        api_model="gpt-3.5-turbo",
        enable_ReAct_prompting=True,
    ):
        if api_key == "" or api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key != "":
            openai.api_key = api_key
        else:
            raise Exception("Please provide OpenAI API key")

        if api_base == "" or api_base is None:
            api_base = os.environ.get(
                "OPENAI_API_BASE", ""
            )  # if not set, use the default base path of "https://api.openai.com/v1"
        if api_base != "":
            # e.g. https://api.openai.com/v1/ or your custom url
            openai.api_base = api_base
            print(f"Using custom api_base {api_base}")

        if api_model == "" or api_model is None:
            api_model = os.environ.get("OPENAI_API_MODEL", "")
        if api_model != "":
            self.api_model = api_model
        else:
            self.api_model = "text-davinci-003"
        print(f"Using api_model {self.api_model}")

        self.use_chat_api = "gpt" in self.api_model

        # reference : https://www.promptingguide.ai/techniques/react
        self.ReAct_prompt = ""
        if enable_ReAct_prompting:
            self.ReAct_prompt = "Write down your observations in format 'Observation:xxxx', then write down your thoughts in format 'Thoughts:xxxx'."

        self.strategy = strategy
        self.evaluation_strategy = evaluation_strategy

        self.client = OpenAI(
            # This is the default and can be omitted
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

        if not os.path.exists("data"):
            os.mkdir("data")
        if not os.path.exists("data/openai.logs"):
            with open("data/openai.logs", "w") as log_file:
                log_file.write("")
        if not os.path.exists("data/tokens.json"):
            with open("data/tokens.json", "w") as token_file:
                init_data = {
                    "dates": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "tokens_used": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "successful_requests": 0,
                    "total_cost": 0,
                    "action_cost": 0,
                }
                json.dump(init_data, token_file)


    def cache_api_call_handler(self, prompt, max_tokens, temperature, k=1, stop=None):
        if os.path.exists(".cache"):
            if not os.path.exists(".cache/openai.cache"):
                with open(".cache/openai.cache", "w") as cache_file:
                    json.dump({}, cache_file)
                return None
            
            with open(".cache/openai.cache", "r") as cache_file:
                cache = json.load(cache_file)
        else:
            os.mkdir(".cache")
            with open(".cache/openai.cache", "w") as cache_file:
                json.dump({}, cache_file)
            cache = {}
        
        if prompt in cache:
            return cache[prompt]
        else:
            return None
    
    def save_cache(self, prompt, response):
        if os.path.exists(".cache"):
            if not os.path.exists(".cache/openai.cache"):
                with open(".cache/openai.cache", "w") as cache_file:
                    json.dump({}, cache_file)
                return None
            with open(".cache/openai.cache", "r") as cache_file:
                cache = json.load(cache_file)
        else:
            os.mkdir(".cache")
            with open(".cache/openai.cache", "w") as cache_file:
                json.dump({}, cache_file)
            cache = {}

        cache[prompt] = response
        with open(".cache/openai.cache", "w") as cache_file:
            json.dump(cache, cache_file)

    def openai_api_call_handler(self, prompt, max_tokens, temperature, k=1, stop=None):
        while True:
            try:
                if self.use_chat_api:
                    messages = [{"role": "user", "content": prompt}]
                    response = self.client.chat.completions.create(
                        model=self.api_model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                else:
                    # print(f"Prompt: {prompt}")
                    response = self.client.completions.create(
                        model=self.api_model,
                        prompt=prompt,
                        n=k,
                        max_tokens=max_tokens,
                        stop=stop,
                        temperature=temperature,
                    )
                with open("data/openai.logs", "a") as log_file:
                    log_file.write(
                        "\n" + "-----------" + "\n" + "Prompt : " + prompt + "\n"
                    )
                return response
            except Exception as e:
                sleep_duratoin = os.environ.get("OPENAI_RATE_TIMEOUT", 30)
                print(
                    f"{str(e)}, sleep for {sleep_duratoin}s, set it by env OPENAI_RATE_TIMEOUT"
                )
                time.sleep(sleep_duratoin)

    def openai_choice2text_handler(self, choice):
        if self.use_chat_api:
            text = choice.message.content
        else:
            text = choice.text.strip()
        return text

    def generate_text(self, prompt, k):
        if self.use_chat_api:
            thoughts = []
            for _ in range(k):
                response = self.openai_api_call_handler(prompt, 400, 0.5, k)
                text = self.openai_choice2text_handler(response.choices[0])
                thoughts += [text]
                # print(f'thoughts: {thoughts}')
            return thoughts

        else:
            response = self.openai_api_call_handler(prompt, 300, 0.5, k)
            thoughts = [
                self.openai_choice2text_handler(choice) for choice in response.choices
            ]
            return thoughts

    def generate_thoughts(self, state, k, initial_prompt, rejected_solutions=None):
        if type(state) == str:
            state_text = state
        else:
            state_text = "\n".join(state)
        print("New state generating thought:", state, "\n\n")
        # prompt = f"Considering the thoughts you've had until now:\n\n{state_text}\n\nDevise the next coherent thought that will aid in advancing the reasoning process and achieving a solution to {initial_prompt}. Assess various scenarios, think unconventionally, anticipate potential challenges, and resolve any outstanding queries. Tap into your mind's full potential and make certain no open questions remain."
        prompt = f"""You're an TreeofThoughts, an superintelligent AI model devoted to helping Humans by any means necessary. You're purpose is to generate a series of solutions to comply with the user's instructions, you must generate solutions on the basis of determining the most reliable solution in the shortest amount of time, while taking rejected solutions into account and learning from them. 
        Considering the reasoning provided:\n\n
        ###'{state_text}'\n\n###
        Devise the best possible solution for the task: {initial_prompt}, Here are evaluated solutions that were rejected: 
        ###{rejected_solutions}###, 
        complete the {initial_prompt} without making the same mistakes you did with the evaluated rejected solutions. Be simple. Be direct. Provide intuitive solutions as soon as you think of them."""

        prompt += self.ReAct_prompt
        # print(prompt)
        thoughts = self.generate_text(prompt, k)
        # print(thoughts)
        # print(f"Generated thoughts: {thoughts}")
        return thoughts

    def generate_solution(self, initial_prompt, state, rejected_solutions=None):
        try:
            if isinstance(state, list):
                state_text = "\n".join(state)
            else:
                state_text = state

            prompt = f"""You're an TreeofThoughts, an superintelligent AI model devoted to helping Humans by any means necessary. You're purpose is to generate a series of solutions to comply with the user's instructions, you must generate solutions on the basis of determining the most reliable solution in the shortest amount of time, while taking rejected solutions into account and learning from them. 
            Considering the reasoning provided:\n\n
            ###'{state_text}'\n\n###
            Devise the best possible solution for the task: {initial_prompt}, Here are evaluated solutions that were rejected: 
            ###{rejected_solutions}###, 
            complete the {initial_prompt} without making the same mistakes you did with the evaluated rejected solutions. Be simple. Be direct. Provide intuitive solutions as soon as you think of them."""
            answer = self.generate_text(prompt, 1)
            print(f"Answer {answer}")
            # print(thoughts)
            # print(f"General Solution : {answer}")
            return answer
        except Exception as e:
            logger.error(f"Error in generate_solutions: {e}")
            return None

    def evaluate_states(self, states, initial_prompt):
        if not states:
            return {}

        if self.evaluation_strategy == "value":
            state_values = {}
            for state in states:
                if type(state) == str:
                    state_text = state
                else:
                    state_text = "\n".join(state)
                print(
                    "We receive a state of type",
                    type(state),
                    "For state: ",
                    state,
                    "\n\n",
                )
                # prompt = f"Given the current state of reasoning: '{state_text}', evaluate its value as a float between 0 and 1, become very pessimistic think of potential adverse risks on the probability of this state of reasoning achieveing {initial_prompt} and DO NOT RESPOND WITH ANYTHING ELSE: OTHER THAN AN FLOAT"
                prompt = f""" To achieve the following goal: '{initial_prompt}', pessimistically value the context of the past solutions and more importantly the latest generated solution you had AS A FLOAT BETWEEN 0 AND 1\n
                    Past solutions:\n\n
                    {state_text}\n       
                    If the solutions is not directly concretely making fast progress in achieving the goal, give it a lower score.
                    Evaluate all solutions AS A FLOAT BETWEEN 0 and 1:\n,  DO NOT RETURN ANYTHING ELSE
                """
                # and then inside backticks provide an simple and direct bulletpoint list as to why you evaluated this thought the way you did. Provide simple yet intuitive feedback.

                response = self.openai_api_call_handler(prompt, 10, 1)
                try:
                    value_text = self.openai_choice2text_handler(response.choices[0])
                    # print(f'state: {value_text}')
                    value = float(value_text)
                    print(f"Evaluated Thought Value: {value}")
                except ValueError:
                    value = 0  # Assign a default value if the conversion fails
                state_values[state] = value
            return state_values

        elif self.evaluation_strategy == "vote":
            states_text = "\n".join([" ".join(state) for state in states])

            prompt = f"Given the following states of reasoning, vote for the best state utilizing an scalar value 1-10:\n{states_text}\n\nVote, on the probability of this state of reasoning achieveing {initial_prompt} and become very pessimistic very NOTHING ELSE"

            response = self.openai_api_call_handler(prompt, 50, 1)

            print(f"state response: {response}")

            best_state_text = self.openai_choice2text_handler(response.choices[0])

            print(f"Best state text: {best_state_text}")

            best_state = tuple(best_state_text.split())

            print(f"best_state: {best_state}")

            return {state: 1 if state == best_state else 0 for state in states}

        else:
            raise ValueError("Invalid evaluation strategy. Choose 'value' or 'vote'.")

    '''
    {
        "dates": "2024-01-03 17:37:50",
        "tokens_used": 3313,
        "prompt_tokens": 3190,
        "completion_tokens": 123,
        "successful_requests": 2,
        "total_cost": 0.0034360000000000007,
        "action_cost": 12.795095205307007
    }
    "usage": {
        "prompt_tokens": 13,
        "completion_tokens": 7,
        "total_tokens": 20
    }
    '''
    def update_token_usage(self, usage):
        with open("data/tokens.json", "r") as token_file:
            tokens = json.load(token_file)
        tokens["dates"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        tokens["tokens_used"] += usage.prompt_tokens + usage.completion_tokens
        tokens["prompt_tokens"] += usage.prompt_tokens
        tokens["completion_tokens"] += usage.completion_tokens
        tokens["successful_requests"] += 1
        if self.api_model == "gpt-3.5-turbo":
            tokens["total_cost"] += 0.001 * usage.prompt_tokens * 0.001 + 0.0002 * usage.completion_tokens * 0.001
        if self.api_model == "gpt-4":
            tokens["total_cost"] += 0.03 * usage.prompt_tokens * 0.001 + 0.06 * usage.completion_tokens * 0.001
        if self.api_model == "gpt-4-turbo":
            tokens["total_cost"] += 0.01 * usage.prompt_tokens * 0.001 + 0.03 * usage.completion_tokens * 0.001

        with open("data/tokens.json", "w") as token_file:
            json.dump(tokens, token_file)

    def few_shot_generate_thoughts(self, system_prompt:str = "", example_prompt:[str] or str = [], max_tokens=2048, temperature=0.0, k=1, stop=None, cache_enabled=True, api_model=""):
        if type(example_prompt) == str:
            example_prompt = [example_prompt]

        assert self.use_chat_api == True, "few shot generation only support chat api"
        assert len(example_prompt) % 2 == 0 or len(example_prompt) == 1, "example prompt should be even number or 1"

        if cache_enabled:
            prompt = str(system_prompt) + "\n" + "\n".join(example_prompt)
            content = self.cache_api_call_handler(prompt, max_tokens, temperature, k, stop)
            if content is not None:
                return content
        while True:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                if len(example_prompt) == 1:
                    messages.append({"role": "user", "content": example_prompt[0]})
                else:
                    for idx in range(0, len(example_prompt), 2):
                        messages.append({"role": "user", "content": example_prompt[idx]})
                        messages.append({"role": "assistant", "content": example_prompt[idx+1]})
                if api_model == "":
                    api_model = self.api_model
                response = self.client.chat.completions.create(
                    model=api_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                self.update_token_usage(response.usage)

                content = response.choices[0].message.content
                if cache_enabled:
                    self.save_cache(prompt, content)
                with open("data/openai.logs", "a") as log_file:
                    log_file.write(
                        "\n" + "-----------" + "\n" + "Prompt : " + str(messages) + "\n"
                    )
                return content
            except Exception as e:
                sleep_duratoin = os.environ.get("OPENAI_RATE_TIMEOUT", 30)
                print(
                    f"{str(e)}, sleep for {sleep_duratoin}s, set it by env OPENAI_RATE_TIMEOUT"
                )
                time.sleep(sleep_duratoin)

    def tree_of_thoughts(self, method, initial_prompt, num_thoughts, max_steps, max_states, value_threshold, pruning_threshold=0.5):
        try:
            if method == TotType.TreeofThoughtsASearch:
                tree = TreeofThoughtsASearch(self)
                response = tree.solve(initial_prompt, num_thoughts, max_steps, pruning_threshold)

            elif method == TotType.TreeofThoughtsBFS:
                tree = TreeofThoughtsBFS(self)
                response = tree.solve(initial_prompt,num_thoughts,max_steps,max_states,value_threshold,pruning_threshold)

            elif method == TotType.TreeofThoughtsDFS:
                tree = TreeofThoughtsDFS(self)
                response = tree.solve(initial_prompt,num_thoughts,max_steps,value_threshold,pruning_threshold)

            elif method == TotType.TreeofThoughtsMonteCarlo:
                tree = MonteCarloTreeofThoughts(self)
                response = tree.solve(initial_prompt, num_thoughts, max_steps, max_states, pruning_threshold)

            elif method == TotType.TreeofThoughtsBEST:
                tree = TreeofThoughtsBEST(self)
                response = tree.solve(initial_prompt, num_thoughts, max_steps, pruning_threshold)
            
            else:
                raise Exception("Invalid method")
            
            return response
        except Exception as e:
            logger.error(f"Error in tree_of_thoughts: {e}")
            return None

            

                
class OptimizedOpenAILanguageModel(OpenAILanguageModel):
    def __init__(
        self,
        api_key,
        strategy="cot",
        evaluation_strategy="value",
        cache_enabled=True,
        api_base="",
        api_model="",
        enable_ReAct_prompting=False,
    ):
        super().__init__(
            api_key,
            strategy,
            evaluation_strategy,
            api_base,
            api_model,
            enable_ReAct_prompting,
        )
        self.cache_enabled = cache_enabled
        self.thought_cache = {}
        self.state_evaluation_cache = {}

    def parallel_generate_thoughts(self, states, k):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            thoughts = list(
                executor.map(lambda state: self.generate_thoughts(state, k), states)
            )
            print(f"Parallel generated thoughts: {thoughts}")
        return thoughts

    def parallel_evaluate_states(self, states, initial_prompt):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            state_values = list(
                executor.map(self.evaluate_states, states, initial_prompt)
            )
            print(f"Parallel evaluated state values: {state_values}")
        return state_values
