import klara


if __name__ == "__main__":
    source = """
        def main(number: int, cm: int, dc: int, wn: int):
            mc = 0
            if wn > 2:
                if number > 2 and number > 2 or number > 2:
                    if number > 0:
                        if wn > 2 or wn > 2:
                            mc = 2
                        else:
                            mc = 5
                    else:
                        mc = 100
            else:
                mc = 1
            pc = number * cm
            if cm <= 4:
                pc_incr = 4
            else:
                pc_incr = cm
            n_pc_incr = pc / pc_incr
            pc_left = dc * pc_incr * (n_pc_incr / 2 + n_pc_incr % 2)
            pc_right = pc - pc_left
            is_rebuf = pc_right
            if is_rebuf:
                cell = Component(pc_right, options=[mc])
            else:
                cell = Component(pc_right)
            return cell
    """
    klara.parse(source)
