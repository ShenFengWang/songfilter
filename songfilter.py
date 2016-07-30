#!/usr/bin/python3
import pymysql
import os
import re

mysql_host = 'localhost'
mysql_user = 'root'
mysql_pwd  = ''

try:
    mysql = pymysql.connect(host = mysql_host, user = mysql_user, password = mysql_pwd, database = 'songfilter', charset = 'utf8mb4', cursorclass = pymysql.cursors.DictCursor)
except pymysql.err.InternalError:
    pass
except Exception as e:
    exit(e)

def formatPath(path):
    if path[0] == "~":
        path = os.path.expanduser(path)
    return os.path.realpath(path)

def validatePath(path, createPath=True):
    if not os.path.exists(path):
        if createPath:
            try:
                os.makedirs(path, mode = 0o771, exist_ok = True)
            except Exception as e:
                print("! Unable to create dir: ", end = "")
                exit(e)
        else:
            return False
    return True


class Configuration:

    cfgId = None

    def __init__(self, name):
        queryCondition = "`is_default` = 1" if name is True else "`alias` = '%s'" % name
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `id`,`storehouse` FROM `config` WHERE %s" % queryCondition)
            configData = cursor.fetchone()
            if not configData:
                if type(name) == str:
                    raise Exception("No configuration named '%s', you should create it with '-C' or '--newcfg'" % name)
                else:
                    raise Exception("No active configuration, please assign one first with '-u' or '--use'")
            elif not configData['storehouse']:
                raise Exception("No storehouse assigned, please assign one first with '-s' or '--storehouse'")
            else:
                self.cfgId = configData['id']

    def getSetting(self, field):
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `%s` FROM `config` WHERE `id` = %s" % (field, self.cfgId))
            return cursor.fetchone()

    def updateSetting(self, field, value):
        with mysql.cursor() as cursor:
            cursor.execute("UPDATE `config` SET `%s` = '%s' WHERE `id` = %d" % (field, value, self.cfgId))
            mysql.commit()
        return mysql.affected_rows()

    def getCfgData(self, alias):
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `id`,`is_default` FROM `config` WHERE `alias` = %s", alias)
            cofigData = cursor.fetchone()
        if not configData:
            raise Exception("No configuration named '%s', you should create it with '-C' or '--newcfg'" % alias)
        else:
            return configData

    def getScfgId(self, alias=None):
            if alias is None:
                configData = self.getSetting('storehouse')
                return configData['storehouse']
            else:
                with mysql.cursor() as cursor:
                    cursor.execute("SELECT `id` FROM `storehouse_cfg` WHERE `alias` = %s", alias)
                    storehouseData = cursor.fetchone()
                if not storehouseData:
                    raise Exception("No storehouse named '%s'" % alias)
                return storehouseData['id']

    def showSuffix(self):
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `suffix` FROM `suffix` WHERE `configid` = %s ORDER BY `order_num`", self.cfgId)
            suffixData = cursor.fetchall()
            suffix = ", ".join(map(lambda x: x['suffix'], suffixData))
            print("Suffix: " + suffix)

    def updateSuffix(self, val):
        suffix = val.split(",")
        with mysql.cursor() as cursor:
            cursor.execute("DELETE FROM `suffix` WHERE `configid` = %s", self.cfgId)
            for index,name in enumerate(suffix):
                cursor.execute("INSERT INTO `suffix` (`suffix`,`configid`,`order_num`) VALUES (%s, %s, %s)",(name, self.cfgId, index))
            mysql.commit()

    def handleArgument(self, target, val):
        if val is True:
            queryData = self.getSetting(target)
            title = target.replace("_", " ").capitalize() + ":"
            print(title, queryData[target])
        else:
            self.updateSetting(target, val)

    def showScfgUsed(self):
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `alias`,`store_path` FROM `storehouse_cfg` WHERE `id` = %s", self.getScfgId())
            storehouseData = cursor.fetchone()
        print("Storehouse name: '%(alias)s', path: '%(store_path)s'" % storehouseData)

    def renameScfg(self, oldname, newname):
        scfgId = self.getScfgId(oldname)
        try:
            self.getScfgId(newname)
        except Exception:
            isExist = True
        else:
            isExist = False
        if isExist:
            raise Exception("New name is used, please enter another one")
        with mysql.cursor() as cursor:
            cursor.execute("UPDATE `storehouse_cfg` SET `alias` = %s WHERE `id` = %s", (newname, scfgId))
            mysql.commit()

    def showCfg(self):
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `alias`,`is_default` FROM `config`")
            configData = cursor.fetchall()
        print("Configuration list:")
        for line in configData:
            print(" " * 4 + ("[*] " if line['is_default'] else "[ ] ") + line['alias'])

    def setDefaultCfg(alias):
        cfg = self.getCfgData(alias)
        if not cfg['is_default']:
            with mysql.cursor() as cursor:
                cursor.execute("UPDATE `config` SET `is_default` = 0")
                cursor.execute("UPDATE `config` SET `is_default` = 1 WHERE `id` = %s", cfg['id'])
                mysql.commit()

    def showScfg(self):
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `alias`,`store_path` FROM `storehouse_cfg`")
            storehouseData = cursor.fetchall()
        print("Storehouse list:")
        print(" " * 4 + "%-30s%s" % ("[name]", "[store path]"))
        for line in storehouseData:
            print(" " * 4 + "%-30s%s" % (line['alias'], line['store_path']))

    def updateStorePath(self, path, alias=None):
        path = formatPath(path)
        validatePath(path)
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `alias` FROM `storehouse_cfg` WHERE `store_path` = %s", path)
            usedHouse = cursor.fetchone()
        if usedHouse:

            raise Exception("The path '%s' is used by storehouse '%s', please enter another path" % (path, usedHouse['alias']))
        try:
            scfgId = self.getScfgId(alias)
        except Exception:
            with mysql.cursor() as cursor:
                cursor.execute("INSERT INTO `storehouse_cfg` (`alias`,`store_path`) VALUES (%s,%s)", (alias, path))
                mysql.commit()
        else:
            with mysql.cursor() as cursor:
                cursor.execute("UPDATE `storehouse_cfg` SET `store_path` = %s WHERE `id` = %s", (path, scfgId))
                mysql.commit()

    def removeStorehouse(self, alias):
        scfgId = self.getScfgId(alias)
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `alias` FROM `config` WHERE `storehouse` = %s", scfgId)
            usedCfg = cursor.fetchone()
            if usedCfg:
                raise Exception("Delete Error, the storehouse '%s' is used by the configuration '%s', you should modify it first" % (alias, usedCfg['alias']))
            cursor.execute("DELETE FROM `storehouse_cfg` WHERE `id` = %s", scfgId)
            mysql.commit()

    def addCfg(self, alias, storehouseAlias=None):
        try:
            cfg = self.getCfgData(alias)
        except Exception:
            isExist = True
        else:
            isExist = False
        if isExist:
            raise Exception("The configuration name '%s' has been used, please enter another one" % alias)
        if storehouseAlias:
            scfgId = self.getScfgId(storehouseAlias)
            field  = "`alias`,`storehouse`"
            value  = "'%s',%d" % (alias, scfgId)
        else:
            field  = "`alias`"
            value  = "'%s'" % alias
        with mysql.cursor() as cursor:
            cursor.execute("INSERT INTO `config` (%s) VALUES (%s)" % (field, value))
            mysql.commit()

    def removeCfg(self, alias):
        cfg = self.getCfgData(alias)
        if cfg['is_default'] == 1 or cfg['id'] == self.cfgId:
            raise Exception("Delete Error, unable to remove the configuration which is being used")
        with mysql.cursor() as cursor:
            cursor.execute("DELETE FROM `config` WHERE `id` = %s", cfg['id'])
            mysql.commit()

    def listCfg(self):
        print("Configuration name: %s" % self.getSetting('alias')['alias'])
        for name in ('split_singer_song', 'split_singers', 'ignore_regex', 'filter_type', 'suffix_cover', 'format_filename'):
            self.handleArgument(name, True)
        self.showSuffix()
        self.showScfgUsed()

    def renameCfg(self, newname):
        try:
            self.getCfgData(newname)
        except Exception:
            isExist = False
        else:
            isExist = True
        if isExist:
            raise Exception("New name is used, please enter another one")
        self.updateSetting('alias', newname)


class Validation:

    cfg = None

    def __init__(self):
        cfgId = Configuration(True).cfgId
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `config`.*,`storehouse_cfg`.`alias` as `storehouse_name`,`storehouse_cfg`.`store_path` FROM `config` JOIN `storehouse_cfg` ON `config`.`storehouse` = `storehouse_cfg`.`id` WHERE `config`.`id` = %s", cfgId)
            self.cfg = cursor.fetchone()
            validatePath(self.cfg['store_path'])
            cursor.execute("SELECT `suffix` as `name`,`order_num` FROM `suffix` WHERE `configid` = %s ORDER BY `order_num`", cfgId)
            self.cfg['suffix'] = cursor.fetchall()
        self.cfg['suffix_name'] = [x['name'] for x in self.cfg['suffix']]

    def getSplitext(self, path):
        basename = os.path.basename(path)
        splitname = os.path.splitext(basename)
        return {'name' : splitname[0], 'ext' : splitname[1][1:]}

    def filterSuffix(self, files):
        result = []
        if files:
            for path in files:
                split = self.getSplitext(path)
                if split['ext'] in self.cfg['suffix_name']:
                    result.append(path)
        return result

    def filterIgnore(self, files):
        result = []
        if files:
            for path in files:
                split = self.getSplitext(path)
                if re.search(self.cfg['ignore_regex'], split['name']) is None:
                    result.append(path)
        return result

    def getStandardFiles(self, files=None):
        if files:
            for index,name in enumerate(files):
                files[index] = formatPath(name)
            originFiles = [path for path in files if validatePath(path, False)]
        else:
            presentPath = os.getcwd()
            files = os.listdir()
            originFiles = [presentPath + "/" + name for name in files if os.path.isfile(presentPath + "/" + name)]
        if self.cfg['ignore_regex']:
            originFiles = self.filterIgnore(originFiles)
        return self.filterSuffix(originFiles)



if __name__ == "__main__":

    import argparse
    commandParser = argparse.ArgumentParser()
    commandParser.add_argument('-x', '--suffix',       nargs  = '?', const = True, type = str)
    commandParser.add_argument('-i', '--ignore',       nargs  = '?', const = True, type = str)
    commandParser.add_argument('-d', '--deletecfg',    nargs  = '?', const = True, type = str)
    commandParser.add_argument('-D', '--deletehouse',  nargs  = '?', const = True, type = str)
    commandParser.add_argument('-u', '--use',          nargs  = '?', const = True, type = str)
    commandParser.add_argument('-L', '--splitsong',    nargs  = '?', const = True, type = str)
    commandParser.add_argument('-l', '--splitsingers', nargs  = '?', const = True, type = str)
    commandParser.add_argument('-v', '--cover',        nargs  = '?', const = True, type = int, choices = (0, 1))
    commandParser.add_argument('-t', '--filtertype',   nargs  = '?', const = True, type = int, choices = (1, 2, 3))
    commandParser.add_argument('-o', '--format',       nargs  = '?', const = True, type = int, choices = (0, 1))
    commandParser.add_argument('-S', '--storepath',    nargs  = '*') #create new house and modify path: newname newpath / oldname newpath;False -> showScfg
    commandParser.add_argument('-C', '--newcfg',       nargs  = '*') #create new cfg, required cfgname [,storehouse]
    commandParser.add_argument('-s', '--storehouse',   nargs  = '*') #oldname newname
    commandParser.add_argument('-c', '--config',       nargs  = '*') #oldname newname
    commandParser.add_argument('-f', '--filter',       nargs  = '*')
    commandParser.add_argument('-a', '--add',          action = 'store_true')
    commandParser.add_argument('-p', '--print',        action = 'store_true')
    commandParser.add_argument('-q', '--quiet',        action = 'store_true')
    commandParser.add_argument('-r', '--report',       action = 'store_true')
    args = commandParser.parse_args()

    def getCfgClass():
        try:
            if args.config and args.config.__len__() > 1:
                raise Exception("too many argumens with '-c' or '--config'")
            cfg = Configuration(args.config[0] if args.config else True)
        except Exception as e:
            exit(e)
        return cfg

    # print(args)

    # -S --storepath
    if args.storepath is not None:
        cfg = getCfgClass()
        argsLen = args.storepath.__len__()
        if not argsLen:
            cfg.showScfg()
        elif argsLen in (1, 2):
            try:
                cfg.updateStorePath(args.storepath[1] if argsLen == 2 else args.storepath[0], args.storepath[0] if argsLen == 2 else None)
            except Exception as e:
                exit(e)
        else:
            exit("too many arguments with '-S' or '--storepath'")

    # -C --newcfg
    if args.newcfg is not None:
        cfg = getCfgClass()
        argsLen = args.newcfg.__len__()
        if not argsLen:
            cfg.showCfg()
        elif argsLen in (1, 2):
            try:
                cfg.addCfg(args.newcfg[0], args.newcfg[1] if argsLen == 2 else None)
            except Exception as e:
                exit(e)
        else:
            exit("too many arguments with '-C' or '--newcfg'")

    # -d --deletecfg
    if args.deletecfg is not None:
        cfg = getCfgClass()
        if args.deletecfg is True:
            cfg.showCfg()
        else:
            try:
                cfg.removeCfg(args.deletecfg)
            except Exception as e:
                exit(e)

    # -D --deletehouse
    if args.deletehouse is not None:
        cfg = getCfgClass()
        if args.deletehouse is True:
            cfg.showScfg()
        else:
            try:
                cfg.removeStorehouse(args.deletehouse)
            except Exception as e:
                exit(e)

    # -u --use
    if args.use is not None:
        if args.use is True:
            Configuration.showCfg(None)
        else:
            try:
                Configuration.setDefaultCfg(args.use)
            except Exception as e:
                exit(e)


    # -x --suffix  /  -i --ignore  /  -L --splitsong  /  -l --splitsingers  /  -v --cover  /  -t --filtertype  /  -o --format  /  -s --storehouse
    if args.suffix is not None\
    or args.ignore is not None\
    or args.splitsong is not None\
    or args.splitsingers is not None\
    or args.cover is not None\
    or args.filtertype is not None\
    or args.format is not None\
    or args.storehouse is not None:
        cfg = getCfgClass()
        if args.suffix is not None:
            if args.suffix is True:
                cfg.showSuffix()
            else:
                cfg.updateSuffix(args.suffix)
        if args.ignore is not None:
            cfg.handleArgument("ignore_regex", args.ignore)
        if args.splitsong is not None:
            cfg.handleArgument("split_singer_song", args.splitsong)
        if args.splitsingers is not None:
            cfg.handleArgument("split_singers", args.splitsingers)
        if args.cover is not None:
            cfg.handleArgument("suffix_cover", args.cover)
        if args.filtertype is not None:
            cfg.handleArgument("filter_type", args.filtertype)
        if args.format is not None:
            cfg.handleArgument("format_filename", args.format)
        if args.storehouse is not None:
            argsLen = args.storehouse.__len__()
            if not argsLen:
                cfg.showScfgUsed()
            elif argsLen == 1:
                try:
                    cfg.updateSetting("storehouse", cfg.getScfgId(args.storehouse[0]))
                except Exception as e:
                    exit(e)
            elif argsLen == 2:
                try:
                    cfg.renameScfg(args.storehouse[0], args.storehouse[1])
                except Exception as e:
                    exit(e)
            else:
                exit("too many arguments with '-s' or '--storehouse'")
    # -c --config
    elif args.config is not None:
        argsLen = args.config.__len__()
        if argsLen <= 1:
            cfg = getCfgClass()
            cfg.listCfg()
        elif argsLen == 2:
            cfg = Configuration(args.config[0])
            cfg.rename(args.config[1])
        else:
            exit("too many arguments with '-c' or '--config'")

    # -f --filter
    # -a --add / -p --print -q --quiet
    if args.filter is not None:
        if not args.quiet:
            print("Starting filter files")
        try:
            vd = Validation()
            standardFiles  = vd.getStandardFiles(args.filter)
            if not args.quiet:
                print(" " * 4 + "Get standard files:")
                if not standardFiles:
                    print(" " * 8 + "no file")
                else:
                    for path in standardFiles:
                        print(" " * 8 + path)
                    filterType = {1 : "name and hash", 2 : "file name", 3 : "file hash"}
                    print(" " * 4 + "Filtering (%s):" % filterType[vd.cfg['filter_type']])
        except Exception as e:
            exit(e)
    # -r --report
    elif args.report:
        pass


mysql.close()
exit(0)
