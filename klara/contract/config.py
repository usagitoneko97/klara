import pathlib

from klara.scripts.cover_gen_ins import config


class ContractConfig(config.ConfigNamespace):
    input_test_file: str = ""
    output_file: str = ""

    def get_output_file(self):
        input_file = pathlib.Path(self.input_test_file)
        if not self.output_file:
            return "test_" + input_file.name
        else:
            return self.output_file
