#!/usr/bin/env python
#  Created by Riley Labrecque for Shorebound Studios
#  This script requires Python 3.3+
#  This script is licensed under the MIT License
#  See the included LICENSE.txt 
#  or the following for more info
#  http://www.tldrlegal.com/license/mit-license

import os

g_files = [f for f in os.listdir('steam') if os.path.isfile(os.path.join('steam', f))]

try:
    os.makedirs('wrapper/')
except OSError:
    pass

g_methodnames = []

for file in g_files:
    print('Opening: ' + file)
    with open('steam/' + file, 'r') as f:
        output = []
        depth = 0
        iface = None
        ifacedepth = 0
        bInMultiLineCommentDepth = False
        for linenum, line in enumerate(f):
            linenum += 1
            bMultiLineCommentCodeOnThisLine = False

            line = line.split('//', 1)[0].strip()
            if len(line) == 0:
                continue

            pos = line.find('/*')
            if pos != -1:
                bInMultiLineCommentDepth = True
                endpos = line.find('*/')
                if endpos != -1:
                    bInMultiLineCommentDepth = False
                else:
                    line = line.split('/*', 1)[0].strip()
                    if len(line) == 0:
                        continue
                    else:
                        bMultiLineCommentCodeOnThisLine = True

            pos = line.find('*/')
            if pos != -1:
                bInMultiLineCommentDepth = False

                line = line[pos+len('*/'):].strip()
                if len(line) == 0:
                    continue

            if bInMultiLineCommentDepth and not bMultiLineCommentCodeOnThisLine:
                continue

            pos = line.find('class ISteam')
            if pos != -1:
                if line.find(';') != -1:
                    continue
                iface = line[pos + len('class '):].split()[0]
                ifacedepth = depth
                print(iface)

            if iface:
                if line.startswith('#'):
                    output.append(line.strip() + '\n')
                elif line.find('virtual') != -1 and line.find(' = 0;') != -1:
                    splitline = line[len('virtual '):].split()
                    state = 0
                    returnvalue = ''
                    methodname = ''
                    realmethodname = ''
                    args = ''
                    for token in splitline:
                        if not token:
                            continue

                        if state == 0:  # Return Value
                            if token[0] == '*':
                                returnvalue += '*'
                                state = 1
                            elif token.find('(') == -1:
                                returnvalue += token + ' '
                            else:
                                state = 1

                        if state == 1:  # Method Name
                            if token[0] == '*':
                                token = token[1:]
                            realmethodname = token.split('(', 1)[0]
                            methodname = iface + '_' + realmethodname

                            if methodname in g_methodnames:
                                methodname += '_'
                            g_methodnames.append(methodname)

                            if token.find(')') == -1:
                                state = 2
                                continue
                            else:
                                state = 3

                        if state == 2:  # Args
                            if token[0] == ')':
                                state = 3
                            elif token.strip() == '*,':  # Edge case in GetClanChatMessage
                                args += '*peChatEntryType, '
                            elif token.strip() == '*':  # Edge case in GetClanChatMessage
                                args += '*pSteamIDChatter '
                            else:
                                args += token + ' '

                        if state == 3:  # ) = 0;
                            continue

                    args = args.rstrip()
                    typelessargs = ''
                    if args != '':
                        argssplitted = args.strip().split(' ')
                        for i, token in enumerate(argssplitted):
                            if token == '*':  # Edge case in GetClanChatMessage
                                typelessargs += '*pSteamIDChatter'
                            elif token == '*,':  # Edge case in GetClanChatMessage
                                typelessargs += '*peChatEntryType,'
                            elif token[0] == '*':
                                typelessargs += token[1:] + ' '
                            elif token[-1] == ',':
                                typelessargs += token + ' '
                            elif i == len(argssplitted) - 1:
                                typelessargs += token
                    typelessargs = typelessargs.rstrip()

                    if returnvalue.strip() == 'CSteamID':
                        returnvalue = 'uint64 '

                    output.append('SB_API ' + returnvalue + methodname + '(' + args + ') {\n')
                    if returnvalue.strip() == 'void':
                        output.append('\t' + iface[1:] + '()->' + realmethodname + '(' + typelessargs + ');\n')
                    elif returnvalue.strip() == 'uint64' and methodname.strip() != 'ISteamUserStats_GetTrophySpaceRequiredBeforeInstall':
                        output.append('\treturn ' + iface[1:] + '()->' + realmethodname + '(' + typelessargs + ').ConvertToUint64();\n')
                    else:
                        output.append('\treturn ' + iface[1:] + '()->' + realmethodname + '(' + typelessargs + ');\n')
                    output.append('}\n')
                    output.append('\n')

            if line.find('{') != -1:
                depth += 1
            if line.find('}') != -1:
                depth -= 1
                if iface and depth == ifacedepth:
                    iface = None

        if output:
            with open('wrapper/' + os.path.splitext(file)[0] + '.cpp', 'w') as out:
                out.write('// This file is automatically generated!\n')
                out.write('#include "steam_api.h"\n')
                out.write('#define SB_API extern "C" __declspec(dllexport)\n')
                out.write('\n')
                for line in output:
                    out.write(line)
