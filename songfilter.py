#!/usr/bin/python3
import pymysql
import os
import re
import hashlib
import shutil
import platform

mysql_host = 'localhost'
mysql_user = 'root'
mysql_pwd  = ''

try:
    mysql = pymysql.connect(host = mysql_host, user = mysql_user, password = mysql_pwd, database = 'songfilter', charset = 'utf8mb4', cursorclass = pymysql.cursors.DictCursor)
except pymysql.err.InternalError:
    mysql = pymysql.connect(host = mysql_host, user = mysql_user, password = mysql_pwd, cursorclass = pymysql.cursors.DictCursor)
    with mysql.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS `songfilter` DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_general_ci")
        cursor.execute("USE `songfilter`")
        cursor.execute("CREATE TABLE `config` (`id` int not null auto_increment primary key,\
                                               `alias` varchar(50) not null,\
                                               `split_singer_song` varchar(255) not null default '',\
                                               `split_singers` varchar(255) not null default '',\
                                               `suffix_cover` tinyint not null default 0,\
                                               `filter_type` tinyint not null default 1,\
                                               `ignore_regex` varchar(255) not null default '',\
                                               `format_filename` tinyint not null default 0,\
                                               `storehouse` int not null default 0,\
                                               `is_default` tinyint not null default 0)")
        cursor.execute("CREATE TABLE `newsongs` (`id` int not null auto_increment primary key,\
                                                 `song_id` int not null,\
                                                 `filename` varchar(255) not null,\
                                                 `storehouse` int not null,\
                                                 `config_id` int not null)")
        cursor.execute("CREATE TABLE `singers` (`id` int not null auto_increment primary key, `name` varchar(100) not null)")
        cursor.execute("CREATE TABLE `songs` (`id` int not null auto_increment primary key,\
                                              `singer_name` varchar(100) not null default '',\
                                              `song_name` varchar(255) not null)")
        cursor.execute("CREATE TABLE `songs_hash` (`id` int not null auto_increment primary key,\
                                                   `song_id` int not null,\
                                                   `file_hash` varchar(40) not null)")
        cursor.execute("CREATE TABLE `storehouse_cfg` (`id` int not null auto_increment primary key,\
                                                       `alias` varchar(30) not null,\
                                                       `store_path` varchar(255) not null)")
        cursor.execute("CREATE TABLE `suffix` (`id` int not null auto_increment primary key,\
                                               `suffix` varchar(10) not null,\
                                               `configid` int not null,\
                                               `order_num` int not null default 0)")
        cursor.execute("CREATE TABLE `storehouse_1` (`id` int not null auto_increment primary key,\
                                                     `song_id` int not null,\
                                                     `file_name` varchar(255) not null,\
                                                     `file_suffix` varchar(10) not null,\
                                                     `save_status` tinyint not null default 0)")
        cursor.execute("INSERT INTO `storehouse_cfg` (`alias`,`store_path`) VALUES (%s, %s)", ("default_storehouse", os.path.realpath(os.getcwd())))
        cursor.execute("INSERT INTO `config` (`alias`,`storehouse`,`is_default`) VALUES ('default_config',1,1)")
        cursor.execute("INSERT INTO `suffix` (`suffix`,`configid`,`order_num`) VALUES ('wav',1,0),('ape',1,1),('flac',1,2),('mp3',1,3)")
        mysql.commit()
    print("INITIALIZE SONGFILTER FINISHED!")
    exit(0)
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

    def clearNewSong(self, scfgId):
        with mysql.cursor() as cursor:
            cursor.execute("DELETE FROM `newsongs` WHERE `storehouse` = %s AND `config_id` = %s", (scfgId, self.cfgId))
            mysql.commit()

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
                suffixName = name.replace(".", "").strip().lower()
                cursor.execute("INSERT INTO `suffix` (`suffix`,`configid`,`order_num`) VALUES (%s, %s, %s)",(suffixName, self.cfgId, index))
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
                scfgId = mysql.insert_id()
                mysql.commit()
                cursor.execute("CREATE TABLE " + "`storehouse_%s`" % scfgId + " (`id` int not null auto_increment primary key,\
                                                                                 `song_id` int not null,\
                                                                                 `file_name` varchar(255) not null,\
                                                                                 `file_suffix` varchar(10) not null,\
                                                                                 `save_status` tinyint not null default 0\
                                                                                 )")
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
    reportPath = "\\total\\" if platform.system() == "Windows" else "/total/"

    def __init__(self):
        cfgId = Configuration(True).cfgId
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `config`.*,`storehouse_cfg`.`alias` as `storehouse_name`,`storehouse_cfg`.`store_path` FROM `config` JOIN `storehouse_cfg` ON `config`.`storehouse` = `storehouse_cfg`.`id` WHERE `config`.`id` = %s", cfgId)
            self.cfg = cursor.fetchone()
            validatePath(self.cfg['store_path'])
            validatePath(self.cfg['store_path'] + self.reportPath)
            cursor.execute("SELECT `suffix` as `name`,`order_num` FROM `suffix` WHERE `configid` = %s ORDER BY `order_num`", cfgId)
            self.cfg['suffix'] = cursor.fetchall()
        self.cfg['suffix_name'] = [x['name'] for x in self.cfg['suffix']]

    def getSplitext(self, path, ignore=True):
        basename = os.path.basename(path)
        splitname = os.path.splitext(basename)
        filename = splitname[0]
        if ignore:
            filename = re.sub("\(.*\)|（.*）|\[.*\]|【.*】|\{.*\}", "", filename)
        return {'name' : filename, 'ext' : splitname[1][1:]}

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
                split = self.getSplitext(path, ignore = False)
                if re.search(self.cfg['ignore_regex'], split['name']) is None:
                    result.append(path)
        return result

    def getStandardFiles(self, files=None, path=None):
        if files:
            for index,name in enumerate(files):
                files[index] = formatPath(name)
            originFiles = [path for path in files if validatePath(path, False)]
        else:
            presentPath = (path.rstrip("\\") if platform.system() == "Windows" else path.rstrip("/")) if path else os.getcwd()
            pathSplit = "\\" if platform.system() == "Windows" else "/"
            files = os.listdir(path if path else ".")
            originFiles = [presentPath + pathSplit + name for name in files if os.path.isfile(presentPath + pathSplit + name)]
        if self.cfg['ignore_regex']:
            originFiles = self.filterIgnore(originFiles)
        return self.filterSuffix(originFiles)

    def getSplitSongFuc(self):
        directionData = self.cfg['split_singer_song'].rsplit("/", 1)
        directionStr = directionData[-1]
        directionStr = "l" if directionStr.lower() == "l" else "r"
        splitFuc = str.split if directionStr == "l" else str.rsplit
        return {"fuc" : splitFuc, "str" : directionData[0], "order" : 0 if directionStr == "l" else -1}

    def splitFile(self, filename):
        if self.cfg['split_singer_song']:
            splitFuc = self.getSplitSongFuc()
            splitedData = splitFuc['fuc'](filename, splitFuc['str'], 1)
            song = splitedData[splitFuc['order']]
            result = {"song" : song.strip()}
            if splitedData.__len__() == 1:
                return result
            originSinger = splitedData[splitFuc['order'] + 1]
            if not self.cfg['split_singers']:
                result['singer'] = [originSinger.strip()]
            else:
                singers = re.split(self.cfg['split_singers'], originSinger)
                result['singer'] = [name.strip() for name in singers]
            return result
        else:
            return {"song" : filename}

    def getSingersId(self, singerList):
        singersId = []
        with mysql.cursor() as cursor:
            for name in singerList:
                cursor.execute("SELECT `id` FROM `singers` WHERE `name` = %s ORDER BY `id`", name)
                singerData = cursor.fetchone()
                if singerData:
                    singersId.append(str(singerData['id']))
                else:
                    return False
        return ",".join(singersId)

    def getSongId(self, fileData=None, fileHash=None):
        if fileData:
            with mysql.cursor() as cursor:
                if not fileData.__contains__("singer"):
                    cursor.execute("SELECT `id` FROM `songs` WHERE `song_name` = %s AND `singer_name` = ''", fileData['song'])
                else:
                    singers = self.getSingersId(fileData['singer'])
                    if not singers:
                        return None
                    cursor.execute("SELECT `id` FROM `songs` WHERE `song_name` = %s AND `singer_name` = %s", (fileData['song'], singers))
                mainSongTableData = cursor.fetchone()
            return mainSongTableData['id'] if mainSongTableData else None
        elif fileHash:
            with mysql.cursor() as cursor:
                cursor.execute("SELECT `song_id` FROM `songs_hash` WHERE `file_hash` = %s", fileHash)
                mainHashTableData = cursor.fetchone()
            return mainHashTableData['song_id'] if mainHashTableData else None
        else:
            return None

    def isNewSongByName(self, fileData):
        songId = self.getSongId(fileData = fileData)
        if not songId:
            return True
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `id` FROM `%s`" % self.getStorehouseTable() + " WHERE `song_id` = %s", songId)
            songData = cursor.fetchone()
            return False if songData else True

    def getExtValue(self, ext):
        extList = self.cfg['suffix_name'][:]
        extList.__reversed__()
        return extList.index(ext)

    def isBetter(self, fileData, newExt):
        songId = self.getSongId(fileData = fileData)
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `file_suffix` FROM `%s`" % self.getStorehouseTable() + " WHERE `song_id` = %s", songId)
            oldExt = cursor.fetchone()['file_suffix']
        if oldExt == newExt:
            return False
        oldExtValue = self.getExtValue(oldExt)
        newExtValue = self.getExtValue(newExt)
        return newExtValue > oldExtValue

    def filterFileName(self, path):
        fileName = self.getSplitext(path)['name']
        filenameData = self.splitFile(fileName)
        filenameData['path'] = path
        if self.isNewSongByName(filenameData):
            filenameData['type'] = "new"
            return filenameData
        elif self.cfg['suffix_cover']:
            fileExt = self.getSplitext(path)['ext']
            if fileExt in self.cfg['suffix_name']:
                if not self.isBetter(filenameData, fileExt):
                    return False
            songId = self.getSongId(fileData = filenameData)
            with mysql.cursor() as cursor:
                cursor.execute("SELECT `save_status` FROM `%s`" % self.getStorehouseTable() + " WHERE `song_id` = %s", songId)
                scfgData = cursor.fetchone()
            if not scfgData['save_status']:
                return False
            filenameData['type'] = "cover"
            filenameData['song_id'] = songId
            return filenameData
        else:
            return False

    def getStorehouseTable(self):
        return "storehouse_" + str(self.cfg['storehouse'])

    def getFileHash(self, path):
        with open(path, "rb") as bFile:
            hashObj = hashlib.sha1()
            hashObj.update(bFile.read())
            return hashObj.hexdigest()

    def isNewSongByHash(self, fileHash):
        songId = self.getSongId(fileHash = fileHash)
        if not songId:
            return True
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `id` FROM `%s`" % self.getStorehouseTable() + " WHERE `song_id` = %s", songId)
            songData = cursor.fetchone()
            return False if songData else True

    def filterFileHash(self, path):
        fileHash = self.getFileHash(path)
        return fileHash if self.isNewSongByHash(fileHash) else False

    def filterFiles(self, path, quiet=False):
        result = []
        filterName = True if self.cfg['filter_type'] == 1 or self.cfg['filter_type'] == 2 else False
        filterHash = True if self.cfg['filter_type'] == 1 or self.cfg['filter_type'] == 3 else False
        for newFile in path:
            if not quiet:
                print(" " * 8 + "[%s]" % newFile)
            if filterName:
                filterNameResult = self.filterFileName(newFile)
                if not quiet:
                    if filterNameResult:
                        songType = "[N]" if filterNameResult['type'] == "new" else "[C]"
                        songName = filterNameResult['song']
                        singerName = filterNameResult['singer'] if filterNameResult.__contains__("singer") else None
                        singerName = ", ".join(singerName) if singerName else " "
                        print(" " * 12 + "%s Song name: %s, Singer name: %s" % (songType, songName, singerName))
                    else:
                        print(" " * 12 + "Filter name: REPEATED SONG")
            else:
                filterNameResult = True
            if filterHash:
                filterHashResult = self.filterFileHash(newFile)
                if not quiet:
                    if filterHashResult:
                        print(" " * 12 + "File hash: %s" % filterHashResult)
                    else:
                        print(" " * 12 + "Filter hash: REPEATED SONG")
            else:
                filterHashResult = True
            if filterNameResult and filterHashResult:
                result.append({"path" : newFile, "name" : filterNameResult, "hash" : filterHashResult})
                if not quiet:
                    print(" " * 12 + "Result: PASS")
            else:
                if not quiet:
                    print(" " * 12 + "Result: REJECT")
            if not quiet:
                print(" ")
        return result

    def formatSingers(self, singerList):
        if not singerList:
            return ""
        with mysql.cursor() as cursor:
            for name in singerList:
                cursor.execute("SELECT `id` FROM `singers` WHERE `name` = %s", name)
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO `singers` (`name`) VALUE (%s)", name)
                    mysql.commit()
        return self.getSingersId(singerList)

    def addSong(self, songName, singerStr):
        with mysql.cursor() as cursor:
            cursor.execute("INSERT INTO `songs` (`singer_name`, `song_name`) VALUES (%s, %s)", (singerStr, songName))
            mysqlInsertId = mysql.insert_id()
            mysql.commit()
            return mysqlInsertId

    def addHash(self, songId, fileHash):
        with mysql.cursor() as cursor:
            cursor.execute("INSERT INTO `songs_hash` (`song_id`, `file_hash`) VALUES (%s, %s)", (songId, fileHash))
            mysql.commit()

    def addTargetStorehouse(self, songId, filename):
        with mysql.cursor() as cursor:
            cursor.execute("INSERT INTO `%s`" % self.getStorehouseTable() + " (`song_id`, `file_name`, `file_suffix`) VALUES (%s, %s, %s)", (songId, filename['name'] ,filename['ext']))
            mysql.commit()

    def updateTargetStorehouse(self, songId, filename):
        with mysql.cursor() as cursor:
            cursor.execute("UPDATE `%s`" % self.getStorehouseTable() + " SET `file_name` = %s, `file_suffix` = %s WHERE `song_id` = %s", (filename['name'], filename['ext'], songId))
            mysql.commit()

    def clearNewSongs(self):
        with mysql.cursor() as cursor:
            cursor.execute("DELETE FROM `newsongs` WHERE `storehouse` = %s", self.cfg['storehouse'])
            mysql.commit()

    def addNewSongs(self, songId, filename):
        with mysql.cursor() as cursor:
            cursor.execute("INSERT INTO `newsongs` (`song_id`, `filename`, `storehouse`, `config_id`) VALUES (%s, %s, %s, %s)", (songId, filename, self.cfg['storehouse'], self.cfg['id']))
            mysql.commit()

    def formatFileName(self, path):
        if self.cfg['format_filename']:
            filename = self.getSplitext(path)
            name = self.splitFile(filename['name'])
            if name.__contains__("singer"):
                singers = ",".join(name['singer'])
                filename['name'] = "%s - %s" % (singers, name['song'])
        else:
            filename = self.getSplitext(path, ignore = False)
        return filename

    def getOldFilename(songId):
        with mysql.cursor() as cursor:
            cursor.execute("SELECT `file_name`, `file_suffix` FROM `%s`" % self.getStorehouseTable() + " WHERE `song_id` = %s", songId)
            oldFile = cursor.fetchone()
            oldFilename = "%s.%s" % (oldFile['file_name'], oldFile['file_suffix'])
            return oldFilename

    def copyFile(self, originFile, targetFile):
        shutil.copy2(originFile, targetFile)

    def updateFile(self, originFile, targetFile, oldFile):
        os.remove(oldFile)
        self.copyFile(originFile, targetFile)


    # newSongs = [ {"path" : str, "name" : {"song" : str, "type": "new"|"cover" [, "singer" : list] [, "song_id" : int]}, "hash" : str|True} ]
    def saveFiles(self, newSongs, quiet=False, add=False):
        if not add:
            self.clearNewSongs()
            if not quiet:
                print(" " * 4 + "Saving:")
        else:
            if not quiet:
                print(" " * 4 + "Saving (ADD):")
        for newSong in newSongs:
            if newSong['name'] is True:
                newSong['name'] = {"name" : self.getSplitext(newSong['path']), "type" : "new"}
            if newSong['hash'] is True:
                newSong['hash'] = self.getFileHash(newSong['path'])
            if newSong['name']['type'] == "new":
                if not quiet:
                    print(" " * 8 + "[N] %s" % newSong['path'])
                singerStr = self.formatSingers(newSong['name']['singer'] if newSong['name'].__contains__("singer") else None)
                if not quiet:
                    print(" " * 12 + "Add song info to main song table")
                newSongId = self.addSong(newSong['name']['song'], singerStr)
                if not quiet:
                    print(" " * 12 + "Add song hash to main hash table")
                self.addHash(newSongId, newSong['hash'])
                filename = self.formatFileName(newSong['path'])
                if not quiet:
                    print(" " * 12 + "Add song info to storehouse table")
                self.addTargetStorehouse(newSongId, filename)
                if not quiet:
                    print(" " * 12 + "Add song info to new song table")
                self.addNewSongs(newSongId, "%s.%s" % (filename['name'], filename['ext']))
                if not quiet:
                    print(" " * 12 + "Copy file to storehouse")
                self.copyFile(newSong['path'], "%s/%s.%s" % (self.cfg['store_path'], filename['name'], filename['ext']))
                if not quiet:
                    print(" " * 12 + "FILENAME: %s.%s" % (filename['name'], filename['ext']))
                    print(" " * 12 + "DONE!")
            else:
                if not quiet:
                    print(" " * 8 + "[C] %s" % newSong['path'])
                    print(" " * 12 + "Add song hash to main hash table")
                self.addHash(newSong['name']['song_id'], newSong['hash'])
                oldFilename = self.getOldFilename(newSong['name']['song_id'])
                newFilenameList = self.formatFileName(newSong['path'])
                newFilename = "%s.%s" % (newFilenameList['name'], newFilenameList['ext'])
                if not quiet:
                    print(" " * 12 + "Update file info for storehouse table")
                self.updateTargetStorehouse(newSong['name']['song_id'], newFilenameList)
                targetPath = self.cfg['store_path'] + self.reportPath
                if not quiet:
                    print(" " * 12 + "Update file for storehouse")
                self.updateFile(newSong, targetPath + newFilename, targetPath + oldFilename)
                if not quiet:
                    print(" " * 12 + "FILENAME: %s" % newFilename)
                    print("DONE!")
        if not quiet:
            print(" ")
            print("TOTAL: %s NEW SONGS ADDED!" % newSongs.__len__())

    def moveFiles(self, originFile, targetFile):
        os.rename(originFile, targetFile)

    def reportFiles(self, quiet=False):
        if not quiet:
            print("Reporting Songs:")
        standardFiles = self.getStandardFiles(path = self.cfg['store_path'])
        if not standardFiles:
            if not quiet:
                print(" " * 4 + "no file")
            return
        if not quiet:
            print(" " * 4 + "Filtering files:")
        for path in standardFiles:
            filename = os.path.basename(path)
            if not quiet:
                print(" " * 8 + "[%s]" % filename)
            with mysql.cursor() as cursor:
                cursor.execute("SELECT `song_id` FROM `newsongs` WHERE `filename` = %s AND `storehouse` = %s AND `config_id` = %s", (filename, self.cfg['storehouse'], self.cfg['id']))
                songData = cursor.fetchone()
                if songData:
                    if not quiet:
                        print(" " * 12 + "Confirm")
                        print(" " * 12 + "Update status")
                    cursor.execute("UPDATE `%s`" % self.getStorehouseTable() + " SET `save_status` = 1 WHERE `song_id` = %s", (songData['song_id']))
                    mysql.commit()
                    if not quiet:
                        print(" " * 12 + "Move file to total directory")
                    self.moveFiles(path, self.cfg['store_path'] + self.reportPath + filename)
                else:
                    if not quiet:
                        print(" " * 12 + "Ignore")
            if not quiet:
                print(" ")
        if not quiet:
            print(" " * 4 + "Clearing table:")
        with mysql.cursor() as cursor:
            cursor.execute("DELETE FROM `newsongs` WHERE `storehouse` = %s", self.cfg['storehouse'])
            mysql.commit()
        if not quiet:
            print(" " * 8 + "DONE!")




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
                    scfgId = cfg.getScfgId(args.storehouse[0])
                    cfg.updateSetting("storehouse", scfgId)
                    cfg.clearNewSong(scfgId)
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
        try:
            vd = Validation()
            if not args.quiet:
                print("Starting filter files:")
            standardFiles = vd.getStandardFiles(args.filter)
            if not args.quiet:
                print(" " * 4 + "Get standard files:")
                if not standardFiles:
                    print(" " * 8 + "no file")
                else:
                    for path in standardFiles:
                        print(" " * 8 + path)
                    print(" ")
            if standardFiles:
                filterType = {1 : "name and hash", 2 : "file name", 3 : "file hash"}
                print(" " * 4 + "Filtering (%s):" % filterType[vd.cfg['filter_type']])
                newSongs = vd.filterFiles(standardFiles, args.quiet)
            else:
                exit(0)
            if newSongs:
                if args.print:
                    exit(0)
                vd.saveFiles(newSongs, args.quiet, args.add)
        except Exception as e:
            exit(e)
    # -r --report
    elif args.report:
        try:
            vd = Validation()
            vd.reportFiles(args.quiet)
        except Exception as e:
            exit(e)


mysql.close()
exit(0)
