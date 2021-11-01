import argparse
import re
import sys
import unicodedata

import chardet


def str_escape(s):
    s = s.replace('\\\\', '\\')
    s = s.replace('\\\'', '\'')
    s = s.replace('\\"', '"')
    s = s.replace('\\n', '\n')
    s = s.replace('\\r', '\r')
    s = s.replace('\\t', '\t')
    s = s.replace('\\0', '')
    return s


parser = argparse.ArgumentParser()
parser.add_argument(
    '-i',
    '--in_filename',
    type=str,
    default='',
    help='input filename, use stdin if omitted',
)
parser.add_argument(
    '-o',
    '--out_filename',
    type=str,
    default='',
    help='output filename, use stdout if omitted',
)
parser.add_argument(
    '--in_encoding',
    type=str,
    default='',
    help='input encoding, auto detect if omitted',
)
parser.add_argument(
    '--out_encoding',
    type=str,
    default='',
    help='output encoding, defaults to the same as input encoding',
)
parser.add_argument(
    '--eol',
    type=str_escape,
    default='\\n',
    help='mark for end of line',
)
parser.add_argument(
    '--max_eol',
    type=int,
    default=2,
    help='maximal number of successive EOL\'s',
)
parser.add_argument(
    '--comment_mark',
    type=str,
    default='',
    help=
    'if this mark appears at the beginning of a line (with leading spaces), the line will not be modified',
)
parser.add_argument(
    '--minor_space',
    type=str_escape,
    default='',
    help='mark for minor spaces',
)
parser.add_argument(
    '--tex_quote',
    action='store_true',
    help='change quote marks to TeX format',
)
parser.add_argument(
    '--zh_period',
    type=str,
    default='empty',
    choices=['free', 'empty', 'dot', 'en_dot'],
    help='format for Chinese periods',
)
parser.add_argument(
    '--zh_quote',
    type=str,
    default='curly',
    choices=['free', 'curly', 'rect', 'straight', 'tex'],
    help='format for Chinese quote marks',
)
parser.add_argument(
    '--guess_lang_window',
    type=int,
    default=4,
    help=
    'number of characters at the beginning and the end of a line to guess the language of the line',
)
parser.add_argument(
    '--normalize_unicode',
    action='store_true',
    help='normalize unicode',
)

args = parser.parse_args()


def zh_letter(c):
    return c >= '\u4e00' and c <= '\u9fa5'


def zh_l_punc(c):
    return c in '（【《￥'


def zh_r_punc(c):
    return c in '，。？！：；）】》'


def zh_m_punc(c):
    return c in '·～—…'


def zh_quote(c):
    return c in '“‘「『”’」』'


def zh_punc(c):
    return zh_l_punc(c) or zh_r_punc(c) or zh_m_punc(c)


def zh_char(c):
    return zh_letter(c) or zh_punc(c) or zh_quote(c)


def en_letter(c):
    return (c >= 'A' and c <= 'Z') or (c >= 'a' and c <= 'z')


def en_l_punc(c):
    return c in '([{@#$'


def en_r_punc(c):
    return c in ',.?!:;)]}%'


def en_r_punc_digit(c):
    return c in '?!;)]}%'


def en_m_punc(c):
    return c in '+-*/\\=<>_^&|~'


def en_quote(c):
    return c in '\'"`'


def en_punc(c):
    return en_m_punc(c) or en_l_punc(c) or en_r_punc(c)


def en_char(c):
    return en_letter(c) or en_punc(c) or en_quote(c)


def letter(c):
    return zh_letter(c) or en_letter(c)


def punc(c):
    return zh_punc(c) or en_punc(c)


def digit(c):
    return c >= '0' and c <= '9'


def correct_full_width(s):
    full_list = ('０', '１', '２', '３', '４', '５', '６', '７', '８', '９', 'Ａ', 'Ｂ',
                 'Ｃ', 'Ｄ', 'Ｅ', 'Ｆ', 'Ｇ', 'Ｈ', 'Ｉ', 'Ｊ', 'Ｋ', 'Ｌ', 'Ｍ', 'Ｎ',
                 'Ｏ', 'Ｐ', 'Ｑ', 'Ｒ', 'Ｓ', 'Ｔ', 'Ｕ', 'Ｖ', 'Ｗ', 'Ｘ', 'Ｙ', 'Ｚ',
                 'ａ', 'ｂ', 'ｃ', 'ｄ', 'ｅ', 'ｆ', 'ｇ', 'ｈ', 'ｉ', 'ｊ', 'ｋ', 'ｌ',
                 'ｍ', 'ｎ', 'ｏ', 'ｐ', 'ｑ', 'ｒ', 'ｓ', 'ｔ', 'ｕ', 'ｖ', 'ｗ', 'ｘ',
                 'ｙ', 'ｚ', '－', '／', '．', '％', '＃', '＠', '＆', '＜', '＞', '［',
                 '］', '｛', '｝', '＼', '｜', '＋', '＝', '＿', '＾', '｀', '‘‘', '’’')

    half_list = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B',
                 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N',
                 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
                 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
                 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
                 'y', 'z', '-', '/', '. ', '%', '#', '@', '&', '<', '>', '[',
                 ']', '{', '}', '\\', '|', '+', '=', '_', '^', '`', '“', '”')

    for full, half in zip(*(full_list, half_list)):
        s = s.replace(full, half)

    return s


def correct_space(s):
    remove_space_type = (
        (zh_char, zh_char),
        (zh_char, digit),
        (digit, zh_char),
        (zh_letter, en_letter),
        (en_letter, zh_letter),
        (zh_letter, en_r_punc),
        (en_l_punc, zh_letter),
        (zh_punc, en_char),
        (en_char, zh_punc),
        (en_letter, en_r_punc),
        (en_l_punc, en_letter),
        (en_l_punc, en_l_punc),
        (en_l_punc, en_r_punc),
        (en_l_punc, en_m_punc),
        (en_r_punc, en_r_punc),
        (en_m_punc, en_r_punc),
        (en_m_punc, en_m_punc),
        (digit, en_r_punc),
        (en_l_punc, digit),
    )

    add_space_type = (
        (zh_letter, en_l_punc),
        (zh_letter, en_m_punc),
        (en_r_punc, zh_letter),
        (en_m_punc, zh_letter),
        (en_letter, en_l_punc),
        (en_letter, en_m_punc),
        (en_r_punc, en_letter),
        (en_m_punc, en_letter),
        (en_r_punc, en_l_punc),
        (en_r_punc, en_m_punc),
        (en_m_punc, en_l_punc),
        (digit, en_l_punc),
        (digit, en_m_punc),
        (en_r_punc_digit, digit),
        (en_m_punc, digit),
    )

    s = list(s)
    for i in range(len(s) - 1):
        if s[i] == ' ':    # i > 0
            for l_type, r_type in remove_space_type:
                if l_type(s[i - 1]) and r_type(s[i + 1]):
                    s[i] = ''
                    break
        else:
            for l_type, r_type in add_space_type:
                if l_type(s[i]) and r_type(s[i + 1]):
                    s[i] += ' '
                    break

    s = ''.join(s).strip()
    return s


def correct_minor_space(s):
    minor_space_type = (
        (zh_letter, en_letter),
        (en_letter, zh_letter),
        (zh_letter, digit),
        (digit, zh_letter),
    )

    s = list(s)
    for i in range(len(s) - 1):
        for l_type, r_type in minor_space_type:
            if l_type(s[i]) and r_type(s[i + 1]):
                s[i] += args.minor_space
                break

    s = ''.join(s).strip()
    return s


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
                range(i, min(i + args.guess_lang_window, j)),
                range(max(j - args.guess_lang_window, i), j)
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


def detect_forward(f, s, i):
    if i == 0:
        return False
    if f(s[i - 1]):
        return True
    if s[i - 1].strip():
        return False
    if i == 1:
        return False
    if f(s[i - 2]):
        return True
    return False


def detect_backward(f, s, i):
    if i == len(s) - 1:
        return False
    if f(s[i + 1]):
        return True
    if s[i + 1].strip():
        return False
    if i == len(s) - 2:
        return False
    if f(s[i + 2]):
        return True
    return False


def correct_punc_zh(s):
    zh_end_punc_list = '，。？！：；'
    en_end_punc_list = ',.?!:;'

    s = list(s)
    for i in range(len(s)):
        for zh_end_punc, en_end_punc in zip(*(zh_end_punc_list,
                                              en_end_punc_list)):
            if s[i] == en_end_punc and detect_forward(zh_char, s, i):
                s[i] = zh_end_punc
                break
        else:
            # 根据括号外部的环境修正括号
            if s[i] == '(' and detect_forward(zh_char, s, i):
                s[i] = '（'
            elif s[i] == ')' and detect_backward(zh_char, s, i):
                s[i] = '）'

            # 根据左括号修正右括号
            if s[i] == '（':
                j = i + 1
                bracket_count = 0
                ok = False
                while j < len(s):
                    if s[j] in ')）':
                        if bracket_count == 0:
                            ok = True
                            break
                        else:
                            bracket_count -= 1
                    elif s[j] in '(（':
                        bracket_count += 1
                    j += 1
                if ok and s[j] == ')':
                    s[j] = '）'

            # 根据右括号修正左括号
            if s[i] == '）':
                j = i - 1
                bracket_count = 0
                ok = False
                while j >= 0:
                    if s[j] in '(（':
                        if bracket_count == 0:
                            ok = True
                            break
                        else:
                            bracket_count -= 1
                    elif s[j] in ')）':
                        bracket_count += 1
                    j -= 1
                if ok and s[j] == '(':
                    s[j] = '（'

    s = ''.join(s).strip()
    return s


def correct_punc_en(s):
    zh_end_punc_list = '，。？！：；'
    en_end_punc_list = ',.?!:;'

    s = list(s)
    for i in range(len(s)):
        for zh_end_punc, en_end_punc in zip(*(zh_end_punc_list,
                                              en_end_punc_list)):
            if s[i] == zh_end_punc and detect_forward(en_char, s, i):
                s[i] = en_end_punc
                break
        else:
            # 根据括号外部的环境修正括号
            if s[i] == '（' and detect_forward(en_char, s, i):
                s[i] = '('
            elif s[i] == '）' and detect_backward(en_char, s, i):
                s[i] = ')'

            # 根据左括号修正右括号
            if s[i] == '(':
                j = i + 1
                bracket_count = 0
                ok = False
                while j < len(s):
                    if s[j] in ')）':
                        if bracket_count == 0:
                            ok = True
                            break
                        else:
                            bracket_count -= 1
                    elif s[j] in '(（':
                        bracket_count += 1
                    j += 1
                if ok and s[j] == '）':
                    s[j] = ')'

            # 根据右括号修正左括号
            if s[i] == ')':
                j = i - 1
                bracket_count = 0
                ok = False
                while j >= 0:
                    if s[j] in '(（':
                        if bracket_count == 0:
                            ok = True
                            break
                        else:
                            bracket_count -= 1
                    elif s[j] in ')）':
                        bracket_count += 1
                    j -= 1
                if ok and s[j] == '（':
                    s[j] = '('

    s = ''.join(s).strip()
    return s


def correct_quote_zh(s):
    s = list(s)
    quote_state = 0
    quote_state_2 = 0
    for i in range(len(s)):
        if s[i] and s[i] in '"“”':
            if quote_state == 0:
                s[i] = '“'
                quote_state = 1
            else:    # quote_state == 1
                s[i] = '”'
                quote_state = 0
            if i > 0 and s[i - 1] == ' ':
                s[i - 1] = ''
            if i < len(s) - 1 and s[i + 1] == ' ':
                s[i + 1] = ''
        elif s[i] and s[i] in '‘’':
            if quote_state_2 == 0:
                s[i] = '‘'
                quote_state_2 = 1
            else:    # quote_state_2 == 1
                s[i] = '’'
                quote_state_2 = 0
            if i > 0 and s[i - 1] == ' ':
                s[i - 1] = ''
            if i < len(s) - 1 and s[i + 1] == ' ':
                s[i + 1] = ''

    s = ''.join(s).strip()
    return s


def correct_quote_en(s):
    s = list(s)
    quote_state = 0
    for i in range(len(s)):
        if s[i] and s[i] in '"“”':
            if quote_state == 0:
                if args.tex_quote:
                    s[i] = '``'
                else:
                    s[i] = '"'
                if i > 0 and s[i - 1] and s[i - 1][-1] != ' ':
                    s[i] = ' ' + s[i]
                if i < len(s) - 1 and s[i + 1] == ' ':
                    s[i + 1] = ''
                quote_state = 1
            else:    # quote_state == 1
                if args.tex_quote:
                    s[i] = '\'\''
                else:
                    s[i] = '"'
                if i > 0 and s[i - 1] and s[i - 1][-1] == ' ':
                    s[i - 1] = s[i - 1][:-1]
                if i < len(s) - 1 and s[i + 1] != ' ':
                    s[i] += ' '
                quote_state = 0
        elif s[i] == '‘':
            if args.tex_quote:
                s[i] = ' `'
            else:
                s[i] = ' \''
        elif s[i] == '’':
            s[i] = '\' '

    s = ''.join(s).strip()
    return s


def correct_ellipsis(s, ellipsis):
    ellipsis_list = '.。·…'

    s = list(s)
    for i in range(len(s)):
        if s[i] and s[i] in ellipsis_list:
            if s[i] == '…':
                ellipsis_count = 3
            else:
                ellipsis_count = 1
            j = i + 1
            while j < len(s):
                if s[j] and s[j] in ellipsis_list:
                    if s[j] == '…':
                        ellipsis_count += 3
                    else:
                        ellipsis_count += 1
                else:
                    break
                j += 1
            if ellipsis_count >= 3:
                s[i] = ellipsis
                for k in range(i + 1, j):
                    s[k] = ''

    s = ''.join(s).strip()
    return s


def correct_zh_period(s):
    if args.zh_period == 'empty':
        s = s.replace('．', '。')
    elif args.zh_period == 'dot':
        s = s.replace('。', '．')
    elif args.zh_period == 'en_dot':
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
        res_line = ' '.join(line.strip().split())

        if not res_line:
            res += args.eol
            continue

        if args.comment_mark and res_line.startswith(args.comment_mark):
            res += line + args.eol
            continue

        if args.normalize_unicode:
            res_line = unicodedata.normalize('NFKC', res_line)

        res_line = correct_full_width(res_line)

        lang = guess_lang(res_line)
        if lang == 'zh':
            while True:
                last_res_line = res_line
                res_line = correct_space(res_line)
                res_line = correct_punc_zh(res_line)
                res_line = correct_quote_zh(res_line)
                res_line = correct_ellipsis(res_line, '……')
                if res_line == last_res_line:
                    break
        else:    # lang == 'en'
            while True:
                last_res_line = res_line
                res_line = correct_space(res_line)
                res_line = correct_punc_en(res_line)
                res_line = correct_quote_en(res_line)
                res_line = correct_ellipsis(res_line, '...')
                if res_line == last_res_line:
                    break

        res_line = correct_minor_space(res_line)
        res_line = correct_zh_period(res_line)
        res_line = correct_zh_quote(res_line)

        res += res_line + args.eol

    res = re.compile(args.eol * (args.max_eol + 1) + '+').sub(
        args.eol * args.max_eol, res)
    return res


def main():
    if args.in_filename:
        if not args.in_encoding:
            with open(args.in_filename, 'rb') as f:
                raw = f.read()
            args.in_encoding = chardet.detect(raw)['encoding']
        with open(args.in_filename, 'r', encoding=args.in_encoding) as f:
            s = f.read()
    else:
        s = sys.stdin.read()

    s = parse_text(s)

    if args.out_filename:
        if not args.out_encoding:
            args.out_encoding = args.in_encoding
        with open(args.out_filename, 'w', encoding=args.out_encoding) as g:
            g.write(s)
    else:
        print(s)


if __name__ == '__main__':
    main()
