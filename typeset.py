import argparse
import chardet
import codecs
import re
import sys
from distutils.util import strtobool


def str_escape(s):
    s = s.replace('\\\\', '\\')
    s = s.replace('\\\'', '\'')
    s = s.replace('\\"', '"')
    s = s.replace('\\n', '\n')
    s = s.replace('\\r', '\r')
    s = s.replace('\\t', '\t')
    return s


parser = argparse.ArgumentParser()
parser.add_argument(
    '-i',
    '--in_filename',
    type=str,
    default='',
    help='input filename, use stdin if omitted')
parser.add_argument(
    '-o',
    '--out_filename',
    type=str,
    default='',
    help='output filename, use stdout if omitted')
parser.add_argument(
    '--in_encoding',
    type=str,
    default='',
    help='input encoding, empty for auto detect')
parser.add_argument(
    '--out_encoding', type=str, default='utf-8', help='output encoding')
parser.add_argument(
    '--eol', type=str_escape, default='\\n', help='mark for end of line')
parser.add_argument(
    '--max_eol',
    type=int,
    default=2,
    help='maximal number of successive EOL\'s')
parser.add_argument(
    '--comment_mark',
    type=str,
    default='',
    help=
    'mark for comment at the beginning of a line, this line will not be modified'
)
parser.add_argument(
    '--minor_space', type=str, default='', help='mark for minor seperation')
parser.add_argument(
    '--tex_quote',
    type=strtobool,
    default=False,
    help='change quote marks to TeX format')
parser.add_argument(
    '--zh_period',
    type=str,
    default='empty',
    choices=['free', 'empty', 'dot', 'en_dot'],
    help='format for Chinese period')
parser.add_argument(
    '--zh_quote',
    type=str,
    default='curly',
    choices=['free', 'curly', 'rect', 'straight', 'tex'],
    help='format for Chinese quote mark')
parser.add_argument(
    '--guess_lang_window',
    type=int,
    default=4,
    help=
    'number of characters at the beginning and the end of a line to guess the language of this line'
)

# Export parameters to global namespace
args = parser.parse_args()
for key in sorted(vars(args)):
    globals()[key] = getattr(args, key)


def zh_letter(c):
    return c >= '\u4e00' and c <= '\u9fa5'


def zh_m_punc(c):
    return c in '·～'


def zh_l_punc(c):
    return c in '（【《“'


def zh_r_punc(c):
    return c in '，。？！：；）】》”'


def zh_punc(c):
    return zh_m_punc(c) or zh_l_punc(c) or zh_r_punc(c)


def en_letter(c):
    return (c >= 'A' and c <= 'Z') or (c >= 'a' and c <= 'z')


def en_m_punc(c):
    return c in '@#$&+-*/%=_^~|\\\'"`<>'


def en_l_punc(c):
    return c in '('


def en_r_punc(c):
    return c in ',.?!:;)'


def en_punc(c):
    return en_m_punc(c) or en_l_punc(c) or en_r_punc(c)


def digit(c):
    return c >= '0' and c <= '9'


def letter(c):
    return zh_letter(c) or en_letter(c)


def correct_full_width(s):
    full = ('０', '１', '２', '３', '４', '５', '６', '７', '８', '９', 'Ａ', 'Ｂ', 'Ｃ',
            'Ｄ', 'Ｅ', 'Ｆ', 'Ｇ', 'Ｈ', 'Ｉ', 'Ｊ', 'Ｋ', 'Ｌ', 'Ｍ', 'Ｎ', 'Ｏ', 'Ｐ',
            'Ｑ', 'Ｒ', 'Ｓ', 'Ｔ', 'Ｕ', 'Ｖ', 'Ｗ', 'Ｘ', 'Ｙ', 'Ｚ', 'ａ', 'ｂ', 'ｃ',
            'ｄ', 'ｅ', 'ｆ', 'ｇ', 'ｈ', 'ｉ', 'ｊ', 'ｋ', 'ｌ', 'ｍ', 'ｎ', 'ｏ', 'ｐ',
            'ｑ', 'ｒ', 'ｓ', 'ｔ', 'ｕ', 'ｖ', 'ｗ', 'ｘ', 'ｙ', 'ｚ', '－', '／', '．',
            '％', '＃', '＠', '＆', '＜', '＞', '［', '］', '｛', '｝', '＼', '｜', '＋',
            '＝', '＿', '＾', '｀', '‘‘', '’’')

    half = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C',
            'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
            'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c',
            'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p',
            'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '-', '/', '. ',
            '%', '#', '@', '&', '<', '>', '[', ']', '{', '}', '\\', '|', '+',
            '=', '_', '^', '`', '“', '”')

    for i in range(len(full)):
        s = s.replace(full[i], half[i])
    return s


def correct_space(s):
    add_space_type = (
        (zh_letter, en_letter),
        (en_letter, zh_letter),
        (zh_letter, en_m_punc),
        (en_m_punc, zh_letter),
        (zh_letter, digit),
        (digit, zh_letter),
        (letter, en_l_punc),
        (en_r_punc, letter),
        (en_r_punc, en_l_punc),
    )

    remove_space_type = (
        (zh_letter, zh_letter),
        (zh_punc, zh_punc),
        (zh_letter, zh_punc),
        (zh_punc, zh_letter),
        (letter, en_r_punc),
        (en_l_punc, letter),
        (en_l_punc, en_l_punc),
        (en_r_punc, en_r_punc),
        (en_l_punc, en_r_punc),
        (zh_punc, en_punc),
        (en_punc, zh_punc),
    )

    clist = list(s)
    for i in range(len(clist) - 1):
        for l_type, r_type in add_space_type:
            if l_type(clist[i]) and r_type(clist[i + 1]):
                clist[i] += ' '
                break
        else:
            if clist[i] == ' ':  # i > 0
                for l_type, r_type in remove_space_type:
                    if l_type(clist[i - 1]) and r_type(clist[i + 1]):
                        clist[i] = ''
                        break
    return ''.join(clist).strip()


def guess_lang(s):
    i = 0
    j = len(s) - 1
    while i < j and not zh_letter(s[i]) and not en_letter(s[i]):
        i += 1
    while i < j and not zh_letter(s[j]) and not en_letter(s[j]):
        j -= 1
    if i >= j:
        return 'zh'

    zh_count = 0
    en_count = 0
    for k in [
            k for ran in [
                range(i, min(i + guess_lang_window, j)),
                range(max(j - guess_lang_window, i), j)
            ] for k in ran
    ]:
        if zh_letter(s[k]):
            zh_count += 1
        elif en_letter(s[k]):
            en_count += 1
    if zh_count * 2 >= en_count:
        return 'zh'
    else:
        return 'en'


def correct_punc(s):
    zh_end_punc = '，。？！：；'
    en_end_punc = ',.?!:;'

    clist = list(s)
    lang = guess_lang(s)
    quote_state = 0
    for i in range(0, len(clist)):
        if lang == 'zh':
            for punc_id in range(len(zh_end_punc)):
                if clist[i] == en_end_punc[punc_id] and i > 0 and zh_letter(
                        clist[i - 1]):
                    clist[i] = zh_end_punc[punc_id]
                    if i < len(clist) - 1 and clist[i + 1] == ' ':
                        clist[i + 1] = ''
                    break
            else:
                if clist[i] == '(' and i > 1 and (zh_letter(clist[i - 2])
                                                  or zh_punc(clist[i - 2])):
                    clist[i] = '（'
                    if clist[i - 1] == ' ':
                        clist[i - 1] = ''
                elif clist[i] == ')' and i < len(clist) - 2 and (zh_letter(
                        clist[i + 2]) or zh_punc(clist[i + 2])):
                    clist[i] = '）'
                    if clist[i + 1] == ' ':
                        clist[i + 1] = ''
                elif clist[i] in ['"', '“', '”']:
                    if quote_state == 0:
                        clist[i] = '“'
                        quote_state = 1
                    else:  # quote_state == 1
                        clist[i] = '”'
                        quote_state = 0
                    if i > 0 and clist[i - 1] == ' ':
                        clist[i - 1] = ''
                    if i < len(clist) - 1 and clist[i + 1] == ' ':
                        clist[i + 1] = ''
            # 修改用于表示比例的冒号
            if clist[i] == '：' and i > 0 and i < len(clist) - 1 and digit(
                    clist[i - 1]) and digit(clist[i + 1]):
                clist[i] = ':'
            # 根据左括号修改右括号
            if clist[i] == '（':
                j = i + 1
                bracket_count = 0
                ok = False
                while j <= len(clist) - 1:
                    if clist[j] == ')' or clist[j] == '）':
                        if bracket_count == 0:
                            ok = True
                            break
                        else:
                            bracket_count -= 1
                    elif clist[j] == '(' or clist[j] == '（':
                        bracket_count += 1
                    j += 1
                if ok and clist[j] == ')':
                    clist[j] = '）'
                    if j < len(clist) - 1 and clist[j + 1] == ' ':
                        clist[j + 1] = ''
            # 根据右括号修改左括号
            if clist[i] == '）':
                j = i - 1
                bracket_count = 0
                ok = False
                while j >= 0:
                    if clist[j] == '(' or clist[j] == '（':
                        if bracket_count == 0:
                            ok = True
                            break
                        else:
                            bracket_count -= 1
                    elif clist[j] == ')' or clist[j] == '）':
                        bracket_count += 1
                    j -= 1
                if ok and clist[j] == '(':
                    clist[j] = '（'
                    if j > 0 and clist[j - 1] == ' ':
                        clist[j - 1] = ''
        else:  # lang == 'en'
            for punc_id in range(len(zh_end_punc)):
                if clist[i] == zh_end_punc[punc_id] and i > 0 and en_letter(
                        clist[i - 1]):
                    clist[i] = en_end_punc[punc_id] + ' '
                    break
            else:
                if clist[i] == '（' and i > 1 and (zh_letter(clist[i - 2])
                                                  or zh_punc(clist[i - 2])):
                    clist[i] = ' ('
                    if clist[i - 1] == ' ':
                        clist[i - 1] = ''
                elif clist[i] == '）' and i < len(clist) - 2 and (zh_letter(
                        clist[i + 2]) or zh_punc(clist[i + 2])):
                    clist[i] = ')'
                    if clist[i + 1] == ' ':
                        clist[i + 1] = ''
                elif clist[i] in ['"', '“', '”']:
                    if quote_state == 0:
                        if tex_quote:
                            clist[i] = ' ``'
                        else:
                            clist[i] = '"'
                        quote_state = 1
                    else:  # quote_state == 1
                        if tex_quote:
                            clist[i] = '\'\' '
                        else:
                            clist[i] = '"'
                        quote_state = 0
                    if i > 0 and clist[i - 1] == ' ':
                        clist[i - 1] = ''
                    if i < len(clist) - 1 and clist[i + 1] == ' ':
                        clist[i + 1] = ''
                # 将中文撇号改为英文
                elif clist[i] == '’' and i > 0 and en_letter(clist[i - 1]):
                    clist[i] = '\''
            # 根据左括号修改右括号
            if clist[i] == '(':
                j = i + 1
                bracket_count = 0
                ok = False
                while j <= len(clist) - 1:
                    if clist[j] == ')' or clist[j] == '）':
                        if bracket_count == 0:
                            ok = True
                            break
                        else:
                            bracket_count -= 1
                    elif clist[j] == '(' or clist[j] == '（':
                        bracket_count += 1
                    j += 1
                if ok and clist[j] == '）':
                    clist[j] = ') '
                    if j < len(clist) - 1 and clist[j + 1] == ' ':
                        clist[j + 1] = ''
            # 根据右括号修改左括号
            if clist[i] == ')':
                j = i - 1
                bracket_count = 0
                ok = False
                while j >= 0:
                    if clist[j] == '(' or clist[j] == '（':
                        if bracket_count == 0:
                            ok = True
                            break
                        else:
                            bracket_count -= 1
                    elif clist[j] == ')' or clist[j] == '）':
                        bracket_count += 1
                    j -= 1
                if ok and clist[j] == '（':
                    clist[j] = ' ('
                    if j > 0 and clist[j - 1] == ' ':
                        clist[j - 1] = ''
    return ''.join(clist).strip()


def correct_minor_space(s):
    minor_space_type = (
        (zh_letter, en_letter),
        (en_letter, zh_letter),
        (zh_letter, digit),
        (digit, zh_letter),
    )

    clist = list(s)
    for i in range(1, len(clist) - 1):
        if clist[i] == ' ':
            for l_type, r_type in minor_space_type:
                if l_type(clist[i - 1]) and r_type(clist[i + 1]):
                    clist[i] = minor_space
                    break
    return ''.join(clist).strip()


def correct_zh_period(s):
    if zh_period == 'empty':
        s = s.replace('．', '。')
    elif zh_period == 'dot':
        s = s.replace('。', '．')
    elif zh_period == 'en_dot':
        s = s.replace('。', '. ')
        s = s.replace('．', '. ')
    return s


def correct_zh_quote(s):
    if zh_quote == 'curly':
        s = s.replace('「', '“')
        s = s.replace('」', '”')
        s = s.replace('『', '‘')
        s = s.replace('』', '’')
    elif zh_quote == 'rect':
        s = s.replace('“', '「')
        s = s.replace('”', '」')
        s = s.replace('‘', '『')
        s = s.replace('’', '』')
    elif zh_quote == 'straight':
        s = s.replace('“', ' "')
        s = s.replace('”', '" ')
        s = s.replace('‘', ' \'')
        s = s.replace('’', '\' ')
        s = s.replace('「', ' "')
        s = s.replace('」', '" ')
        s = s.replace('『', ' \'')
        s = s.replace('』', '\' ')
    elif zh_quote == 'tex':
        s = s.replace('“', ' ``')
        s = s.replace('”', '\'\' ')
        s = s.replace('‘', ' `')
        s = s.replace('’', '\' ')
        s = s.replace('「', ' ``')
        s = s.replace('」', '\'\' ')
        s = s.replace('『', ' `')
        s = s.replace('』', '\' ')
    return s


def parse_text(s):
    if not s:
        return ''

    res = ''
    for line in s.splitlines():
        if line and comment_mark and line.startswith(comment_mark):
            res += line + eol
            continue

        res_line = ' '.join(line.split())
        if res_line == '':
            res += eol
            continue

        res_line = correct_full_width(res_line)
        res_line = correct_space(res_line)
        res_line = correct_punc(res_line)
        res_line = correct_space(res_line)
        res_line = correct_punc(res_line)
        res_line = correct_minor_space(res_line)
        res_line = correct_zh_period(res_line)
        res_line = correct_zh_quote(res_line)
        res += res_line + eol
    res = re.compile(eol * max_eol + eol + '+').sub(eol * max_eol, res)
    return res


if __name__ == '__main__':
    if in_filename:
        if not in_encoding:
            with open(in_filename, 'rb') as f:
                raw = f.read()
            in_encoding = chardet.detect(raw)['encoding']
        with codecs.open(in_filename, 'r', in_encoding) as f:
            s = f.read()
    else:
        s = sys.stdin.read()
    s = parse_text(s)
    if out_filename:
        with codecs.open(out_filename, 'w', out_encoding) as g:
            g.write(s)
    else:
        print(s)
