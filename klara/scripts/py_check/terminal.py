from textwrap import dedent


class TerminalFormatter:
    def __init__(self, realdir, result, config=None, tempdir=None):
        self.tempdir = tempdir
        self.result = result
        self.realdir = realdir
        self.config = config
        self.warning_count = 0

    @staticmethod
    def get_src_line(source_str, lineno, strip=True):
        source_str = source_str.splitlines()[lineno - 1]
        return (source_str.lstrip(), (len(source_str) - len(source_str.strip()))) if strip else source_str

    def get_error_result_on_path(self, source_str, collected_result, last_file=None):
        output = ""
        if collected_result:
            for trace, items_in_trace in collected_result.items():
                description_str = "Floating point comparison detected. Please fix the float variable as shown below.\n"
                trace_str = self.get_full_traceback(items_in_trace, last_file)
                items_str = ""
                for lineno in sorted(items_in_trace.warning):
                    items_in_line = items_in_trace.warning[lineno]
                    self.sort_item_by_col(items_in_line)
                    src, white_space_number = self.get_src_line(source_str, lineno)
                    caret_str = self.get_caret(items_in_line, white_space_number)
                    items_str += "line: {}\n{}\n{}\n".format(lineno, src, caret_str)
                    items_str += self.get_items_value_repr(items_in_line)
                output = output + description_str + trace_str + items_str + "\n"
        return output

    @staticmethod
    def sort_item_by_col(item):
        item.sort(key=lambda x: x.col_offset, reverse=False)

    @staticmethod
    def get_caret(warning_items, white_space_number=0):
        """
        get the caret pointing to each of the item in the col
        :param warning_items: items presented in a line
        :param white_space_number: the total number of leading space
        :return: str: full caret _str
        """
        caret_str = ""
        for each_col_item in warning_items:
            if (each_col_item.col_offset - len(caret_str) - white_space_number) >= 0:
                caret_str = caret_str + ((" " * (each_col_item.col_offset - len(caret_str) - white_space_number)) + "^")
        return caret_str

    def get_items_value_repr(self, warning_items):
        """
        format a full representation of items and their values. E.g.:
        x = 1 {<int>}
        :param warning_items: items presented in a line
        :return: str: the items with their values
        """
        result_str = ""
        recorded_var = []
        self.warning_count += 1
        for each_col_item in warning_items:
            if each_col_item.value_repr not in recorded_var:
                recorded_var.append(each_col_item.value_repr)
                if each_col_item.value_repr is not None:
                    if not self.config.is_hiding_value():
                        result_str += "{} = {} ({})\n".format(
                            each_col_item.value_repr, each_col_item.value, each_col_item.optional_type
                        )
                    else:
                        result_str += "{} ({})\n" "".format(each_col_item.value_repr, each_col_item.optional_type)
        return result_str

    def get_full_traceback(self, warning_items, last_file):
        """
        format a complete traceback str, that depends on the verbose config
        :param warning_items: items presented in a line
        :param last_file: the actual file that warning_items collected
        :return: str: formatted trace str
        """
        if self.config.verbose == 2:
            trace_str = self.get_traceitem_list(warning_items.trace)
        else:
            try:
                trace_str = 'File "{}"\nIn {}\n'.format(
                    warning_items.trace[-1].filename, warning_items.trace[-1].name.name
                )
            except AttributeError:
                trace_str = 'File "{}"\nIn {}\n'.format(warning_items.trace[-1].filename, warning_items.trace[-1][2])
        return trace_str

    def get_traceitem_list(self, trace):
        s = dedent(
            """\
                Traceback (most recent call last):
                """
        )
        for t in trace[:-1]:
            s += self.get_traceback_item(t)
        try:
            s += 'File "{}"\nIn {}\n'.format(trace[-1].filename, str(trace[-1].name))
        except AttributeError:
            s += 'File "{}"\nIn {}\n'.format(trace[-1].filename, trace[-1][2])
        return s

    def get_traceback_item(self, trace):
        return 'File "{}" line {}, in {}\n{}\n'.format(trace.filename, trace.lineno, trace.name.name, str(trace.line))

    def get_full_errors(self):
        output = ""
        for base_path, collected_result in self.result.items():
            output += (
                self.get_error_result_on_path(base_path.replace("fcf_", ""), collected_result, base_path)
                + "---------------------------------\n"
            )
        return output

    def get_summary(self):
        if self.warning_count > 0:
            return "Total number of floating-point warnings captured: {}\n".format(self.warning_count)
        return ""
