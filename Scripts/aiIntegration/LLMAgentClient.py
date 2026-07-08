class RossbotAgentClient:
    def __init__(self, llm_client, tts_client, command_client):
        self.llm_client = llm_client
        self.tts_client = tts_client
        self.command_client = command_client

    def respond(self, user_text):
        llm_response = self.llm_client.generate(user_text)

        expression, spoken_text = self.parse_llm_response(llm_response)

        self.command_client.send_commands([
            {"type": "expression", "name": expression}
        ])

        mouth_cues, audio = self.tts_client.create_speech(spoken_text)

        self.command_client.send_commands([
            {"type": "speak", "syllables": mouth_cues}, {"type":"play","audio":audio}
        ])

        

class debug_screen():
    pass