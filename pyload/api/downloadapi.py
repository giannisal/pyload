# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import str
from os.path import isabs

from pyload.Api import Api, require_perm, Permission, Role
from pyload.utils.fs import join

from .apicomponent import ApiComponent


class DownloadApi(ApiComponent):
    """ Component to create, add, delete or modify downloads."""

    # TODO: workaround for link adding without owner
    def true_primary(self):
        if self.user:
            return self.user.true_primary
        else:
            return self.pyload.db.getUserData(role=Role.Admin).uid

    @require_perm(Permission.Add)
    def create_package(self, name, folder, root, password="", site="", comment="", paused=False):
        """Create a new package.

        :param name: display name of the package
        :param folder: folder name or relative path, abs path are not allowed
        :param root: package id of root package, -1 for top level package
        :param password: single pw or list of passwords separated with new line
        :param site: arbitrary url to site for more information
        :param comment: arbitrary comment
        :param paused: No downloads will be started when True
        :return: pid of newly created package
        """

        if isabs(folder):
            folder = folder.replace("/", "_")

        folder = folder.replace("http://", "").replace(":", "").replace("\\", "_").replace("..", "")

        self.pyload.log.info(_("Added package %(name)s as folder %(folder)s") % {"name": name, "folder": folder})
        pid = self.pyload.files.addPackage(name, folder, root, password, site, comment, paused, self.truePrimary())

        return pid


    @require_perm(Permission.Add)
    def add_package(self, name, links, password="", paused=False):
        """Convenient method to add a package to the top-level and for adding links.

        :return: package id
        """
        return self.addPackageChild(name, links, password, -1, paused)

    @require_perm(Permission.Add)
    def addPackageP(self, name, links, password, paused):
        """ Same as above with additional paused attribute. """
        return self.addPackageChild(name, links, password, -1, paused)

    @require_perm(Permission.Add)
    def add_package_child(self, name, links, password, root, paused):
        """Adds a package, with links to desired package.

        :param root: parents package id
        :return: package id of the new package
        """
        if self.pyload.config['general']['folder_per_package']:
            folder = name
        else:
            folder = ""

        pid = self.createPackage(name, folder, root, password, paused=paused)
        self.addLinks(pid, links)

        return pid

    @require_perm(Permission.Add)
    def add_links(self, pid, links):
        """Adds links to specific package. Initiates online status fetching.

        :param pid: package id
        :param links: list of urls
        """
        hoster, crypter = self.pyload.pluginManager.parseUrls(links)

        self.pyload.files.addLinks(hoster + crypter, pid, self.truePrimary())
        if hoster:
            self.pyload.threadManager.createInfoThread(hoster, pid)

        self.pyload.log.info((_("Added %d links to package") + " #%d" % pid) % len(hoster+crypter))
        self.pyload.files.save()

    @require_perm(Permission.Add)
    def upload_container(self, filename, data):
        """Uploads and adds a container file to pyLoad.

        :param filename: filename, extension is important so it can correctly decrypted
        :param data: file content
        """
        th = open(join(self.pyload.config["general"]["download_folder"], "tmp_" + filename), "wb")
        th.write(str(data))
        th.close()

        return self.addPackage(th.name, [th.name])

    @require_perm(Permission.Delete)
    def remove_files(self, fids):
        """Removes several file entries from pyload.

        :param fids: list of file ids
        """
        for fid in fids:
            self.pyload.files.removeFile(fid)

        self.pyload.files.save()

    @require_perm(Permission.Delete)
    def remove_packages(self, pids):
        """Rempve packages and containing links.

        :param pids: list of package ids
        """
        for pid in pids:
            self.pyload.files.removePackage(pid)

        self.pyload.files.save()


    @require_perm(Permission.Modify)
    def restart_package(self, pid):
        """Restarts a package, resets every containing files.

        :param pid: package id
        """
        self.pyload.files.restartPackage(pid)

    @require_perm(Permission.Modify)
    def restart_file(self, fid):
        """Resets file status, so it will be downloaded again.

        :param fid: file id
        """
        self.pyload.files.restartFile(fid)

    @require_perm(Permission.Modify)
    def recheck_package(self, pid):
        """Check online status of all files in a package, also a default action when package is added. """
        self.pyload.files.reCheckPackage(pid)

    @require_perm(Permission.Modify)
    def restart_failed(self):
        """Restarts all failed failes."""
        self.pyload.files.restartFailed()

    @require_perm(Permission.Modify)
    def stop_all_downloads(self):
        """Aborts all running downloads."""
        for pyfile in self.pyload.files.cachedFiles():
            if self.hasAccess(pyfile):
                pyfile.abortDownload()

    @require_perm(Permission.Modify)
    def stop_downloads(self, fids):
        """Aborts specific downloads.

        :param fids: list of file ids
        :return:
        """
        pyfiles = self.pyload.files.cachedFiles()
        for pyfile in pyfiles:
            if pyfile.id in fids and self.hasAccess(pyfile):
                pyfile.abortDownload()


if Api.extend(DownloadApi):
    del DownloadApi