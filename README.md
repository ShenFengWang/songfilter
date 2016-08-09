SONGFILTER 音乐过滤器
===
    一句话简介：使用PYTHON3和MYSQL数据库，根据文件名或文件哈希过滤重复的歌曲。

特性
---
*   多配置
*   多歌曲库
*   歌曲库和配置一对多
*   文件忽略（正则表达式）
*   格式化文件名
*   相同歌曲替换（文件后缀名）

安装
---
### MYSQL数据库
>sudo apt install mysql

### PYTHON库
>pip3 install pymysql

初始化
---
克隆项目至本地后运行<code>songfilter.py</code>创建数据库和表，并选择当前文件夹作为歌曲库（稍后可再配置）。

选项
---
*   -h  --help  帮助

*   -x  --suffix [suffix1,suffix2,suffix3,...] 显示/修改 （需要执行过滤的）文件后缀名<br>
后缀名以 "," 分割；<br>
当文件替换开启时，若出现同名文件则根据后缀顺序替换，后缀优先级从左至右依次降低（从左至右依次覆盖）；<br>
当使用多配置单一歌曲库时，若文件后缀不在列表中，则总是覆盖；<br>
同名文件：指被过滤文件与已报告的文件（"total"文件夹内）比较。

*   -i  --ignore [str|regex] 显示/修改 需要忽略的文件<br>
若文件名（不包括后缀）中出现指定的字符串则忽略该文件，支持正则表达式。

*   -d  --deletecfg [cfgname]  显示/删除 配置<br>
删除配置，不能删除当前正在使用的配置。

*   -D  --deletehouse [storehousename] 显示/删除 歌曲库<br>
删除歌曲库，不能删除被使用的歌曲库。

*   -u  --use [cfgname] 显示/使用 配置<br>
指定当前使用的配置。

*   -L  --splitsong [str[/l]] 显示/修改 歌手与歌名的分隔符<br>
分割歌手与歌名的字符，仅限字符串，为空时将文件名全部作为歌名；<br>
字符串右侧可添加限定符"/l"或"/r"（忽略大小写），指定左侧（或右侧）为歌名；<br>
若没有限定符，则默认右侧为歌名。

*   -l  --splitsingers [str|regex] 显示/修改 多歌手间的分隔符<br>
当有多名歌手时分割歌手名称，支持正则表达式。

*   -v  --cover [{0,1}] 显示/修改 文件替换<br>
是否开启文件替换。

*   -t  --filtertype [{1,2,3}] 显示/修改 文件过滤方式<br>
文件过滤方式：[1] 文件名和哈希，[2] 文件名，[3] 哈希

*   -o  --format [{0,1}] 显示/修改 格式化文件名<br>
是否开启格式化文件名。

*   -S  --storepath [storehousename[ path]] 显示/创建 歌曲库；修改 歌曲库路径<br>
创建歌曲库：-S 新歌曲库名称 新路径<br>
修改歌曲库路径：-S 已有歌曲库名称 新路径

*   -C  --newcfg [cfgname[ storehousename]] 显示/创建 配置<br>
创建配置：新配置名称 [歌曲库名称]

*   -s  --storehouse [storehousename[ newname]] 显示 （当前/指定）歌曲库信息/修改 歌曲库名称<br>
修改歌曲库名称：-s 原名称 新名称

*   -c  -config [cfgname[ newname]] 显示 （当前/指定）配置的所有配置项信息/修改 配置名称<br>
修改配置名称：-s 原名称 新名称

*   -f  --filter [filewithpath1[ filewithpath2[ filewithpath3[ ...]]]] 当前文件夹/指定文件 执行过滤<br>
执行过滤，并将新歌曲添加进歌曲库。

*   -a  --add 添加模式<br>
当执行完过滤后过滤的新歌曲会被添加进新歌曲列表，当执行报告('-r' or '--report')时根据新歌曲列表校验；<br>
每次过滤前会清空当前配置下的新歌曲列表；<br>
执行过滤后，未执行报告前切换歌曲库会清空新歌曲列表；<br>
开启添加模式，则不清空新歌曲列表。

*   -p  --print 验证模式<br>
仅执行过滤，不将文件添加进歌曲库。

*   -q  --quiet 安静模式<br>
不输出信息。

*   -r  --report 报告<br>
试听过滤后的新歌曲，删除不喜欢的歌曲，将剩下的（喜欢的）歌曲进行报告；<br>
报告后歌曲将被移动至歌曲库"total"文件夹下；<br>
报告后的文件可被执行文件替换，替换的文件直接放置在"total"文件夹。

使用
---
*   初始化
*   配置选项
*   在需要过滤文件的文件夹下执行"songfilter.py -f"
*   试听歌曲，筛选后，执行"songfilter.py -r"

筛选
---
    musicplaycontroller.py（使用audacious播放器）删除歌曲（播放列表及文件）
