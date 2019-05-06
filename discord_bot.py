import copy
import json
import os

import discord
from unidecode import unidecode

from chatbot import libchatbot

try:  # Unicode patch for Windows
    import win_unicode_console

    win_unicode_console.enable()
except:
    if os.name == 'nt':
        import sys

        if sys.version_info < (3, 6):
            print("Please install the 'win_unicode_console' module.")

do_logging = True
log_name = "Discord-Chatbot.log"

model = "reddit"
save_dir = "models/" + model

def_max_input_length = 1000
def_max_length = 125

def_beam_width = 2
def_relevance = -1
def_temperature = 1.0
def_topn = -1

max_input_length = def_max_input_length
max_length = def_max_length

beam_width = def_beam_width
relevance = def_relevance
temperature = def_temperature
topn = def_topn

states_main = "states" + "_" + model

states_folder = states_main + "/" + "server_states"
states_folder_dm = states_main + "/" + "dm_states"

states_saves = states_main + "/" + "saves"

user_settings_folder = "user_settings"
ult_operators_file = user_settings_folder + "/" + "ult_operators.cfg"
operators_file = user_settings_folder + "/" + "operators.cfg"
banned_users_file = user_settings_folder + "/" + "banned_users.cfg"

processing_users = []

mention_in_message = True
mention_message_separator = " - "

message_prefix = ">"
command_prefix = "--"  # Basically treated as message_prefix + command_prefix

ult_operators = []
operators = []
banned_users = []

states_queue = {}

print('Loading Chatbot-RNN...')
lib_save_states, lib_get_states, consumer = libchatbot(
    save_dir=save_dir, max_length=max_length)
print('Chatbot-RNN has been loaded.')

print('Preparing Discord Bot...')
client = discord.Client()


@client.event
async def on_ready():
    print()
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print()
    print('Discord Bot ready!')


def log(message):
    if do_logging:
        with open(log_name, "a", encoding="utf-8") as log_file:
            log_file.write(message)


def load_states(states_id):
    global states_folder, states_folder_dm

    make_folders()

    states_file = get_states_file(states_id)

    if os.path.exists(states_file + ".pkl") and os.path.isfile(states_file + ".pkl"):
        return lib_get_states(states_file)
    else:
        return lib_get_states()


def make_folders():
    if not os.path.exists(states_folder):
        os.makedirs(states_folder)

    if not os.path.exists(states_folder_dm):
        os.makedirs(states_folder_dm)

    if not os.path.exists(user_settings_folder):
        os.makedirs(user_settings_folder)

    if not os.path.exists(states_saves):
        os.makedirs(states_saves)


def get_states_file(states_id):
    if states_id.endswith("p"):
        states_file = states_folder_dm + "/" + states_id
    else:
        states_file = states_folder + "/" + states_id

    return states_file


def save_states(states_id, states=None):  # Saves directly to the file, recommended to use states queue
    make_folders()

    states_file = get_states_file(states_id)

    lib_save_states(states_file, states=states)


def add_states_to_queue(states_id, states_diffs):
    current_states_diffs = None

    if states_id in states_queue:
        current_states_diffs = states_queue[states_id]

    for num in range(len(states_diffs)):
        if current_states_diffs is not None and current_states_diffs[num] is not None:
            states_diffs[num] += current_states_diffs[num]

    states_queue.update({states_id: states_diffs})


def get_states_id(message):
    if message.guild is None or isinstance(message.channel, discord.abc.PrivateChannel):
        return str(message.channel.id) + "p"
    else:
        return str(message.guild.id) + "s"


def write_state_queue():
    for states_id in states_queue:
        states = load_states(states_id)

        states_diff = states_queue[states_id]
        if get_states_size(states) > len(states_diff):
            states = states[0]

        elif get_states_size(states) < len(states_diff):
            states = [copy.deepcopy(states), copy.deepcopy(states)]

        new_states = copy.deepcopy(states)

        total_num = 0
        for num in range(len(states)):
            for num_two in range(len(states[num])):
                for num_three in range(len(states[num][num_two])):
                    for num_four in range(len(states[num][num_two][num_three])):
                        new_states[num][num_two][num_three][num_four] = states[num][num_two][num_three][num_four] - \
                                                                        states_diff[total_num]
                        total_num += 1

        lib_save_states(get_states_file(states_id), states=new_states)
    states_queue.clear()


def get_states_size(states):
    total_num = 0
    if states is not None:
        for num in range(len(states)):
            for num_two in range(len(states[num])):
                for num_three in range(len(states[num][num_two])):
                    for num_four in range(len(states[num][num_two][num_three])):
                        total_num += 1
    return total_num


def is_discord_id(user_id):
    # Quick general check to see if it matches the ID formatting
    return (isinstance(user_id, int) or user_id.isdigit) and len(str(user_id)) == 18


def remove_invalid_ids(id_list):
    for user in id_list:
        if not is_discord_id(user):
            id_list.remove(user)


def save_ops_bans():
    global ult_operators, operators, banned_users

    make_folders()

    # Sort and remove duplicate entries
    ult_operators = list(set(ult_operators))
    operators = list(set(operators))
    banned_users = list(set(banned_users))

    # Remove from list if ID is invalid
    remove_invalid_ids(ult_operators)

    # Remove them from the ban list if they were added
    # Op them if they were removed
    for user in ult_operators:
        operators.append(user)
        if user in banned_users:
            banned_users.remove(user)

    # Remove from list if ID is invalid
    remove_invalid_ids(operators)

    # Remove from list if ID is invalid
    remove_invalid_ids(banned_users)

    # Sort and remove duplicate entries
    ult_operators = list(set(ult_operators))
    operators = list(set(operators))
    banned_users = list(set(banned_users))

    with open(ult_operators_file, 'w') as f:
        f.write(json.dumps(ult_operators))
    with open(operators_file, 'w') as f:
        f.write(json.dumps(operators))
    with open(banned_users_file, 'w') as f:
        f.write(json.dumps(banned_users))


def load_ops_bans():
    global ult_operators, operators, banned_users

    make_folders()

    if os.path.exists(ult_operators_file) and os.path.isfile(ult_operators_file):
        with open(ult_operators_file, 'r') as f:
            try:
                ult_operators = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                ult_operators = []

    if os.path.exists(operators_file) and os.path.isfile(operators_file):
        with open(operators_file, 'r') as f:
            try:
                operators = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                operators = []

    if os.path.exists(banned_users_file) and os.path.isfile(banned_users_file):
        with open(banned_users_file, 'r') as f:
            try:
                banned_users = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                banned_users = []

    save_ops_bans()


# Prepare the operators and ban lists
load_ops_bans()


def matches_command(content, command):
    try:
        content = content[:content.index(" ")]
    except ValueError:
        pass

    return content.lower() == command_prefix.lower() + command.lower()


def remove_command(content):
    try:
        content = content[content.index(" ") + 1:]
    except ValueError:
        content = ""

    return content


def user_id_cleanup(uid):
    return uid.replace("<@", "").replace("!", "").replace(">", "")


def get_args(content):
    return split_args(remove_command(content))


def split_args(full_args):
    return [] if full_args == "" else full_args.split(" ")


def get_user_perms(message):
    load_ops_bans()

    user_perms = {
        "banned": message.author.id in banned_users,
        "op": message.author.id in operators,
        "ult_op": message.author.id in ult_operators,
        "server_admin": message.guild is None or message.author.guild_permissions.administrator,
        "private": message.channel is discord.abc.PrivateChannel,
    }

    return user_perms


def process_response(response, result):
    # 0 = OK
    # 1 = Generic error in arguments
    # 2 = Too many arguments
    # 3 = Not enough arguments
    # 4 = Generic error
    # 5 = No permissions error
    # 6 = User not found error
    # 7 = Command not found error

    error_code_print = False

    if result == 0:
        if response == "":
            response = "Command successful"

        response = "System: " + response
    elif result == 1:
        if response == "":
            response = "Invalid argument(s)"

        response = "Error: " + response
    elif result == 2:
        if response == "":
            response = "Too many arguments"

        response = "Error: " + response
    elif result == 3:
        if response == "":
            response = "Not enough arguments"

        response = "Error: " + response
    elif result == 4:
        if response == "":
            response = "Generic error"
            error_code_print = True

        response = "Error: " + response
    elif result == 5:
        if response == "":
            response = "Insufficient permissions"

        response = "Error: " + response
    elif result == 6:
        if response == "":
            response = "User not found"

        response = "Error: " + response
    elif result == 7:
        if response == "":
            response = "Command not found"

        response = "Error: " + response

    if error_code_print:
        response += " (Error Code " + str(result) + ")"

    return response


async def process_command(msg_content, message):
    global max_input_length, max_length, beam_width, relevance, temperature, topn

    result = 0

    response = ""

    load_ops_bans()
    user_perms = get_user_perms(message)

    cmd_args = get_args(msg_content)

    if matches_command(msg_content, "help"):
        response = "Available Commands:\n" \
                   "```\n" \
                   "help, restart, reset, save, load, op, deop, ban, unban, param_reset," \
                   "max_input_length, max_length, beam_width, temperature, relevance, topn\n" \
                   "```"

    elif matches_command(msg_content, "restart"):
        if user_perms["ult_op"]:
            print()
            print("[Restarting...]")
            response = "System: Restarting..."
            await send_message(message, response)
            client.close()
            exit()
        else:
            result = 5

    elif matches_command(msg_content, "reset"):
        if user_perms["op"] or user_perms["private"] or user_perms["server_admin"]:
            reset_states = lib_get_states()

            save_states(get_states_id(message), states=reset_states)

            print()
            print("[Model state reset]")
            response = "Model state reset"
        else:
            result = 5

    elif matches_command(msg_content, "save"):
        if user_perms["ult_op"]:
            if len(cmd_args) >= 1:
                input_text = cmd_args[0]

                if input_text.endswith(".pkl"):
                    input_text = input_text[:len(input_text) - len(".pkl")]

                make_folders()

                lib_save_states(states_saves + "/" + input_text,
                                states=lib_get_states(get_states_file(get_states_id(message))))

                print()
                print("[Saved states to \"{}.pkl\"]".format(input_text))
                response = "Saved model state to \"{}.pkl\"".format(input_text)
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "load"):
        if user_perms["ult_op"]:
            if len(cmd_args) >= 1:
                input_text = cmd_args[0]

                if input_text.endswith(".pkl"):
                    input_text = input_text[:len(input_text) - len(".pkl")]

                make_folders()

                save_states(get_states_id(message), states=lib_get_states(states_saves + "/" + input_text))

                print()
                print("[Loaded saved states from \"{}.pkl\"]".format(
                    input_text))
                response = "Loaded saved model state from \"{}.pkl\"".format(
                    input_text)
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "op"):
        if user_perms["ult_op"]:
            if len(cmd_args) >= 1:
                # Replacements are to support mentioned users
                input_text = user_id_cleanup(remove_command(msg_content))
                user_exists = True

                # Check if user actually exists
                try:
                    await client.fetch_user(input_text)
                except discord.NotFound:
                    user_exists = False
                except discord.HTTPException:
                    user_exists = False

                if not input_text == str(message.author.id):
                    if user_exists:
                        if not int(input_text) in ult_operators and not int(input_text) == client.user.id:
                            if not int(input_text) in operators:
                                if not int(input_text) in banned_users:
                                    load_ops_bans()
                                    operators.append(int(input_text))
                                    save_ops_bans()
                                    print()
                                    print("[Opped \"{}\"]".format(input_text))
                                    response = "Opped \"{}\".".format(input_text)
                                else:
                                    response = "Unable to op user \"{}\", they're banned".format(input_text)
                                    result = 4
                            else:
                                response = "Unable to op user \"{}\", they're already OP".format(input_text)
                                result = 4
                        else:
                            response = "Unable to op user \"{}\", you do not have permission to do so".format(
                                input_text)
                            result = 3
                    else:
                        response = "Unable to op user \"{}\", they don't exist".format(input_text)
                        result = 6
                else:
                    response = "Unable to op user \"{}\", __that's yourself__...".format(input_text)
                    result = 4
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "deop"):
        if user_perms["ult_op"]:
            if len(cmd_args) >= 1:
                # Replacements are to support mentioned users
                input_text = user_id_cleanup(remove_command(msg_content))
                user_exists = True

                # Check if user actually exists
                try:
                    await client.fetch_user(input_text)
                except discord.NotFound:
                    user_exists = False
                except discord.HTTPException:
                    user_exists = False

                if not input_text == str(message.author.id):
                    if user_exists:
                        if not int(input_text) in ult_operators and not int(input_text) == client.user.id:
                            if int(input_text) in operators:
                                load_ops_bans()
                                if int(input_text) in operators:
                                    operators.remove(int(input_text))
                                save_ops_bans()
                                print()
                                print("[De-opped \"{}\"]".format(input_text))
                                response = "De-opped \"{}\".".format(input_text)
                            else:
                                response = "Unable to de-op user \"{}\", they're not OP".format(input_text)
                                result = 4
                        else:
                            response = "Unable to de-op user \"{}\", you do not have permission to do so".format(
                                input_text)
                            result = 3
                    else:
                        response = "Unable to de-op user \"{}\", they don't exist".format(input_text)
                        result = 6
                else:
                    response = "Unable to de-op user \"{}\", __that's yourself__...".format(input_text)
                    result = 4
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "ban"):
        if user_perms["op"]:
            if len(cmd_args) >= 1:
                # Replacements are to support mentioned users
                input_text = user_id_cleanup(remove_command(msg_content))
                user_exists = True

                # Check if user actually exists
                try:
                    await client.fetch_user(input_text)
                except discord.NotFound:
                    user_exists = False
                except discord.HTTPException:
                    user_exists = False

                if not input_text == str(message.author.id):
                    if user_exists:
                        if not int(input_text) in ult_operators and not int(input_text) == client.user.id:
                            if not int(input_text) in banned_users:
                                load_ops_bans()
                                banned_users.append(int(input_text))
                                save_ops_bans()
                                print()
                                print("[Banned \"{}\"]".format(input_text))
                                response = "Banned \"{}\".".format(input_text)
                            else:
                                response = "Unable to ban user \"{}\", they're already banned".format(input_text)
                                result = 4
                        else:
                            response = "Unable to ban user \"{}\", you do not have permission to do so".format(
                                input_text)
                            result = 3
                    else:
                        response = "Unable to ban user \"{}\", they don't exist".format(input_text)
                        result = 6
                else:
                    response = "Unable to ban user \"{}\", __that's yourself__...".format(input_text)
                    result = 4
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "unban"):
        if user_perms["op"]:
            if len(cmd_args) >= 1:
                # Replacements are to support mentioned users
                input_text = user_id_cleanup(remove_command(msg_content))
                user_exists = True

                # Check if user actually exists
                try:
                    await client.fetch_user(input_text)
                except discord.NotFound:
                    user_exists = False
                except discord.HTTPException:
                    user_exists = False

                if not input_text == str(message.author.id):
                    if user_exists:
                        if not int(input_text) in ult_operators and not int(input_text) == client.user.id:
                            if int(input_text) in banned_users:
                                load_ops_bans()
                                if int(input_text) in banned_users:
                                    banned_users.remove(int(input_text))
                                save_ops_bans()
                                print()
                                print("[Un-banned \"{}\"]".format(input_text))
                                response = "Un-banned \"{}\".".format(input_text)
                            else:
                                response = "Unable to un-ban user \"{}\", they're not banned".format(input_text)
                                result = 4
                        else:
                            response = "Unable to un-ban user \"{}\", you do not have permission to do so".format(
                                input_text)
                            result = 3
                    else:
                        response = "Unable to un-ban user \"{}\", they don't exist".format(input_text)
                        result = 6
                else:
                    response = "Unable to un-ban user \"{}\", __that's yourself__...".format(input_text)
                    result = 4
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "param_reset"):
        if user_perms["ult_op"]:
            max_input_length = def_max_input_length
            max_length = def_max_length

            beam_width = def_beam_width
            relevance = def_relevance
            temperature = def_temperature
            topn = def_topn

            print()
            print("[User \"{}\" reset all params]".format(message.author.id))
            response = "All parameters have been reset."
        else:
            result = 5

    elif matches_command(msg_content, "max_input_length"):
        if user_perms["ult_op"]:
            if len(cmd_args) >= 1:
                input_text = cmd_args[0]

                max_input_length = int(input_text)
                print()
                print("[User \"{}\" changed the max input length to {}]".format(message.author.id, max_input_length))
                response = "Max input length changed to {}.".format(max_input_length)
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "max_length"):
        if user_perms["ult_op"]:
            if len(cmd_args) >= 1:
                input_text = cmd_args[0]

                max_length = int(input_text)
                print()
                print("[User \"{}\" changed the max response length to {}]".format(message.author.id, max_length))
                response = "Max response length changed to {}.".format(max_length)
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "beam_width"):
        if user_perms["op"] or user_perms["private"] or user_perms["server_admin"]:
            if len(cmd_args) >= 1:
                input_text = cmd_args[0]

                beam_width = int(input_text)
                print()
                print("[User \"{}\" changed the beam width to {}]".format(message.author.id, beam_width))
                response = "Beam width changed to {}.".format(beam_width)
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "temperature"):
        if user_perms["op"] or user_perms["private"] or user_perms["server_admin"]:
            if len(cmd_args) >= 1:
                input_text = cmd_args[0]

                temperature = float(input_text)
                print()
                print("[User \"{}\" changed the temperature to {}]".format(message.author.id, temperature))
                response = "Temperature changed to {}.".format(temperature)
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "relevance"):
        if user_perms["op"] or user_perms["private"] or user_perms["server_admin"]:
            if len(cmd_args) >= 1:
                input_text = cmd_args[0]

                relevance = float(input_text)
                print()
                print("[User \"{}\" changed the relevance to {}]".format(message.author.id, relevance))
                response = "Relevance changed to {}.".format(relevance)
            else:
                result = 3
        else:
            result = 5

    elif matches_command(msg_content, "topn"):
        if user_perms["op"] or user_perms["private"] or user_perms["server_admin"]:
            if len(cmd_args) >= 1:
                input_text = cmd_args[0]

                topn = int(input_text)
                print()
                print("[User \"{}\" changed the topn to {}]".format(message.author.id, topn))
                response = "TopN filter changed to {}.".format(topn)
            else:
                result = 3
        else:
            result = 5

    else:
        result = 7

    return process_response(response, result)


def has_channel_perms(message):
    return message.guild is None or message.channel.permissions_for(
        message.guild.get_member(client.user.id)).send_messages;


async def send_message(message, text):
    if (mention_in_message or (not mention_in_message and not text == "")) and has_channel_perms(message):
        user_mention = ""

        if mention_in_message:
            user_mention = "<@" + str(message.author.id) + ">" + mention_message_separator

        await message.channel.send(user_mention + text)


@client.event
async def on_message(message):
    global max_input_length, max_length, beam_width, relevance, temperature, topn, lib_save_states, lib_get_states, consumer

    if message.content.lower().startswith(message_prefix.lower()) or message.channel is discord.abc.PrivateChannel and not message.author.bot and has_channel_perms(message):
        msg_content = message.content

        if msg_content.startswith(message_prefix):
            msg_content = msg_content[len(message_prefix):]
        if msg_content.startswith(" "):
            msg_content = msg_content[len(" "):]

        response = "Error: Unknown error..."

        async with message.channel.typing():
            user_perms = get_user_perms(message)
            if user_perms["banned"] and not user_perms["private"]:
                response = process_response("You have been banned and can only use this bot in DMs", 5)

            elif msg_content.lower().startswith(command_prefix.lower()):
                response = await process_command(msg_content, message)

            else:
                if not (message.author.id in processing_users):
                    if not msg_content == "":
                        if not len(msg_content) > max_input_length:
                            # Possibly problematic: if something goes wrong,
                            # then the user couldn't send messages anymore
                            processing_users.append(message.author.id)

                            states = load_states(get_states_id(message))

                            old_states = copy.deepcopy(states)

                            clean_msg_content = unidecode(message.clean_content)

                            if clean_msg_content.startswith(message_prefix):
                                clean_msg_content = clean_msg_content[len(message_prefix):]
                            if clean_msg_content.startswith(" "):
                                clean_msg_content = clean_msg_content[len(" "):]

                            print()  # Print out new line for formatting
                            print("> " + clean_msg_content)  # Print out user message

                            # Automatically prints out response as it's written
                            result, states = await consumer(clean_msg_content, states=states, beam_width=beam_width, relevance=relevance, temperature=temperature, topn=topn, max_length=max_length)

                            # Purely debug
                            # print(states[0][0][0]) Prints out the lowest level array
                            # for state in states[0][0][0]: Prints out every entry in the lowest level array
                            #     print(state)

                            # Remove whitespace before the message
                            while result.startswith(" "):
                                result = result[1:]

                            if not mention_in_message and result == "":
                                result = "..."

                            response = result

                            print()  # Move cursor to next line after response

                            log("\n> " + msg_content + "\n" + result + "\n")  # Log entire interaction
                            if len(old_states) == len(states):
                                # Get the difference in the states

                                states_diff = []
                                for num in range(len(states)):
                                    for num_two in range(len(states[num])):
                                        for num_three in range(len(states[num][num_two])):
                                            for num_four in range(len(states[num][num_two][num_three])):
                                                states_diff.append(old_states[num][num_two][num_three][num_four] -
                                                                   states[num][num_two][num_three][num_four])

                                add_states_to_queue(get_states_id(message), states_diff)
                                write_state_queue()
                                # save_states(get_states_id(message)) Old saving
                            else:
                                # Revert to old saving to directly write new array dimensions
                                save_states(get_states_id(message))

                            processing_users.remove(message.author.id)
                        else:
                            response = "Error: Your message is too long (" + str(len(msg_content)) + "/" + str(
                                max_input_length) + " characters)"
                    else:
                        response = "Error: Your message is empty"
                else:
                    response = "Error: Please wait for your response to be generated before sending more messages"

        await send_message(message, response)


client.run("Token Goes Here", reconnect=True)
