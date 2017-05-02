import codecs
import re
import sys


encoding = 'utf-8'
eol = '\n'
comment_mark = '\\%'
# my_space = '{\\myspace}'
my_space = ''
ch_period = 'empty'  # free | empty | dot | endot
ch_quote = 'curly'  # free | curly | rect | straight | tex
tex_quote = False
guess_lang_window = 4


def ischletter(c):
    return c >= '\u4e00' and c <= '\u9fa5'


def ischmpunc(c):
    return c in '·～'


def ischlpunc(c):
    return c in '（【《“'


def ischrpunc(c):
    return c in '，。？！：；）】》”'


def ischpunc(c):
    return ischmpunc(c) or ischlpunc(c) or ischrpunc(c)


def isenletter(c):
    return (c >= 'A' and c <= 'Z') or (c >= 'a' and c <= 'z')


def isenmpunc(c):
    return c in '@#$&+-*/%=_^~|\\\'"`<>'


def isenlpunc(c):
    return c in '('


def isenrpunc(c):
    return c in ',.?!:;)'


def isenpunc(c):
    return isenmpunc(c) or isenlpunc(c) or isenrpunc(c)


def isdigit(c):
    return c >= '0' and c <= '9'


def isletter(c):
    return ischletter(c) or isenletter(c)


def correct_full_width(string):
    full = [
        '０', '１', '２', '３', '４',
        '５', '６', '７', '８', '９',
        'Ａ', 'Ｂ', 'Ｃ', 'Ｄ', 'Ｅ',
        'Ｆ', 'Ｇ', 'Ｈ', 'Ｉ', 'Ｊ',
        'Ｋ', 'Ｌ', 'Ｍ', 'Ｎ', 'Ｏ',
        'Ｐ', 'Ｑ', 'Ｒ', 'Ｓ', 'Ｔ',
        'Ｕ', 'Ｖ', 'Ｗ', 'Ｘ', 'Ｙ',
        'Ｚ', 'ａ', 'ｂ', 'ｃ', 'ｄ',
        'ｅ', 'ｆ', 'ｇ', 'ｈ', 'ｉ',
        'ｊ', 'ｋ', 'ｌ', 'ｍ', 'ｎ',
        'ｏ', 'ｐ', 'ｑ', 'ｒ', 'ｓ',
        'ｔ', 'ｕ', 'ｖ', 'ｗ', 'ｘ',
        'ｙ', 'ｚ', '－', '／', '．',
        '％', '＃', '＠', '＆', '＜',
        '＞', '［', '］', '｛', '｝',
        '＼', '｜', '＋', '＝', '＿',
        '＾', '｀', '‘‘', '’’'
    ]
    half = [
        '0', '1', '2', '3', '4',
        '5', '6', '7', '8', '9',
        'A', 'B', 'C', 'D', 'E',
        'F', 'G', 'H', 'I', 'J',
        'K', 'L', 'M', 'N', 'O',
        'P', 'Q', 'R', 'S', 'T',
        'U', 'V', 'W', 'X', 'Y',
        'Z', 'a', 'b', 'c', 'd',
        'e', 'f', 'g', 'h', 'i',
        'j', 'k', 'l', 'm', 'n',
        'o', 'p', 'q', 'r', 's',
        't', 'u', 'v', 'w', 'x',
        'y', 'z', '-', '/', '. ',
        '%', '#', '@', '&', '<',
        '>', '[', ']', '{', '}',
        '\\', '|', '+', '=', '_',
        '^', '`', '“', '”'
    ]

    for i in range(len(full)):
        string = string.replace(full[i], half[i])
    return string


def correct_space(string):
    clist = list(string)
    for i in range(len(clist) - 1):
        if (ischletter(clist[i]) and isenletter(clist[i + 1])) \
                or (isenletter(clist[i]) and ischletter(clist[i + 1])) \
                or (ischletter(clist[i]) and isenmpunc(clist[i + 1])) \
                or (isenmpunc(clist[i]) and ischletter(clist[i + 1])) \
                or (ischletter(clist[i]) and isdigit(clist[i + 1])) \
                or (isdigit(clist[i]) and ischletter(clist[i + 1])) \
                or (isletter(clist[i]) and isenlpunc(clist[i + 1])) \
                or (isenrpunc(clist[i]) and isletter(clist[i + 1])) \
                or (isenrpunc(clist[i]) and isenlpunc(clist[i + 1])):
            clist[i] += ' '
        elif clist[i] == ' ':  # i > 0
            if ((ischletter(clist[i - 1]) or ischpunc(clist[i - 1]))
                    and (ischletter(clist[i + 1]) or ischpunc(clist[i + 1]))) \
                    or (isletter(clist[i - 1]) and isenrpunc(clist[i + 1])) \
                    or (isenlpunc(clist[i - 1]) and isletter(clist[i + 1])) \
                    or (isenrpunc(clist[i - 1]) and isenrpunc(clist[i + 1])) \
                    or (isenlpunc(clist[i - 1]) and isenlpunc(clist[i + 1])) \
                    or (isenlpunc(clist[i]) and isenrpunc(clist[i + 1])) \
                    or (ischpunc(clist[i - 1]) and isenpunc(clist[i + 1])) \
                    or (isenpunc(clist[i - 1]) and ischpunc(clist[i + 1])):
                clist[i] = ''
    return ''.join(clist).strip()


def guess_lang(string):
    while len(string) > 0 \
            and not (ischletter(string[0]) or isenletter(string[0])):
        string = string[1:]
    while len(string) > 0 \
            and not (ischletter(string[-1]) or isenletter(string[-1])):
        string = string[:-1]
    chcount = 0
    encount = 0
    for i in range(len(string)) if len(string) < guess_lang_window * 2 \
            else range(-guess_lang_window, guess_lang_window):
        if ischletter(string[i]):
            chcount += 1
        elif isenletter(string[i]):
            encount += 1
    if chcount * 2 >= encount:
        return 'ch'
    else:
        return 'en'


def correct_punc(string):
    chrpunc = '，。？！：；'
    enrpunc = ',.?!:;'

    clist = list(string)
    lang = guess_lang(string)
    quote_state = 0
    for i in range(0, len(clist)):
        if lang == 'ch':
            for puncid in range(len(chrpunc)):
                if clist[i] == enrpunc[puncid] and i > 0 \
                        and ischletter(clist[i - 1]):
                    clist[i] = chrpunc[puncid]
                    if i < len(clist) - 1 and clist[i + 1] == ' ':
                        clist[i + 1] = ''
                    break
            else:
                if clist[i] == '(' and i > 1  \
                        and (ischletter(clist[i - 2])
                             or ischpunc(clist[i - 2])):
                    clist[i] = '（'
                    if clist[i - 1] == ' ':
                        clist[i - 1] = ''
                elif clist[i] == ')' and i < len(clist) - 2 \
                        and (ischletter(clist[i + 2])
                             or ischpunc(clist[i + 2])):
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
            for puncid in range(len(chrpunc)):
                if clist[i] == chrpunc[puncid] and i > 0 \
                        and isenletter(clist[i - 1]):
                    clist[i] = enrpunc[puncid] + ' '
                    break
            else:
                if clist[i] == '（' and i > 1 \
                        and (ischletter(clist[i - 2])
                             or ischpunc(clist[i - 2])):
                    clist[i] = ' ('
                    if clist[i - 1] == ' ':
                        clist[i - 1] = ''
                elif clist[i] == '）' and i < len(clist) - 2 \
                        and (ischletter(clist[i + 2])
                             or ischpunc(clist[i + 2])):
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
                elif clist[i] == '’' and i > 0 \
                        and isenletter(clist[i - 1]):
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


def correct_my_space(string):
    clist = list(string)
    for i in range(1, len(clist) - 1):
        if clist[i] == ' ' \
                and ((ischletter(clist[i - 1]) and isenletter(clist[i + 1]))
                     or (isenletter(clist[i - 1]) and ischletter(clist[i + 1]))
                     or (ischletter(clist[i - 1]) and isdigit(clist[i + 1]))
                     or (isdigit(clist[i - 1]) and ischletter(clist[i + 1]))):
            clist[i] = my_space
    return ''.join(clist).strip()


def correct_ch_period(string):
    if ch_period == 'empty':
        string = string.replace('．', '。')
    elif ch_period == 'dot':
        string = string.replace('。', '．')
    elif ch_period == 'endot':
        string = string.replace('。', '. ')
        string = string.replace('．', '. ')
    return string


def correct_ch_quote(string):
    if ch_quote == 'curly':
        string = string.replace('『', '“')
        string = string.replace('』', '”')
        string = string.replace('「', '‘')
        string = string.replace('」', '’')
    elif ch_quote == 'rect':
        string = string.replace('“', '『')
        string = string.replace('”', '』')
        string = string.replace('‘', '「')
        string = string.replace('’', '」')
    elif ch_quote == 'straight':
        string = string.replace('“', ' "')
        string = string.replace('”', '" ')
        string = string.replace('‘', ' \'')
        string = string.replace('’', '\' ')
        string = string.replace('『', ' "')
        string = string.replace('』', '" ')
        string = string.replace('「', ' \'')
        string = string.replace('」', '\' ')
    elif ch_quote == 'tex':
        string = string.replace('“', ' ``')
        string = string.replace('”', '\'\' ')
        string = string.replace('‘', ' `')
        string = string.replace('’', '\' ')
        string = string.replace('『', ' ``')
        string = string.replace('』', '\'\' ')
        string = string.replace('「', ' `')
        string = string.replace('」', '\' ')
    return string


def parse_line(string):
    res = ' '.join(string.split())
    if res == '':
        return eol
    if res[0] in comment_mark:
        return string
    res = correct_full_width(res)
    res = correct_space(res)
    res = correct_punc(res)
    res = correct_my_space(res)
    res = correct_ch_period(res)
    res = correct_ch_quote(res)
    res += eol
    return res


def parse_file(filename):
    f = codecs.open(filename, 'r', encoding)
    g = codecs.open(filename + '.out', 'w', encoding)
    for line in f:
        g.write(parse_line(line))
    f.close()
    g.close()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        parse_file(sys.argv[1])
    else:
        print('Usage: python autopunc.py filename')
