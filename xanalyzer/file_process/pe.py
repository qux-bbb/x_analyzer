# coding:utf8

from datetime import datetime
import pefile
import peutils

from signify.signed_pe import SignedPEFile

from xanalyzer.config import Config
from xanalyzer.utils import log


class PeAnalyzer:
    file_path = None
    pe_file = None

    def __init__(self, file_path):
        self.file_path = file_path
        self.pe_file = pefile.PE(self.file_path)
    
    def compile_time_scan(self):
        """
        获取编译时间
        """
        time_str = datetime.fromtimestamp(self.pe_file.FILE_HEADER.TimeDateStamp)
        log.info('compile time: {}'.format(time_str))

    def pdb_scan(self):
        """
        查看pdb路径
        """
        for debug_entry in getattr(self.pe_file, 'DIRECTORY_ENTRY_DEBUG', []):
            if hasattr(debug_entry.entry, 'PdbFileName'):
                log.info('pdb path: {}'.format(debug_entry.entry.PdbFileName.decode('utf8')))
                return

    def peid_scan(self):
        """
        查壳
        """
        signatures = peutils.SignatureDatabase(Config.peid_signature_path)
        matches = signatures.match(self.pe_file, ep_only=True)
        if matches:
            log.info(matches)

    def cert_scan(self):
        """
        输出证书信息并验证
        """
        security_index = pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]
        if len(self.pe_file.OPTIONAL_HEADER.DATA_DIRECTORY) <= security_index:
            return
        security_entry = self.pe_file.OPTIONAL_HEADER.DATA_DIRECTORY[security_index]
        if not security_entry.Size or not security_entry.VirtualAddress:
            return
        with open(self.file_path, 'rb') as f:
            try:
                pe = SignedPEFile(f)
                for signed_data in pe.signed_datas:
                    cert = signed_data.certificates[0]
                    log.info('Contains certificates:')
                    log.info('   Subject: {}'.format(cert.subject_dn))
                    log.info('   Issuer: {}'.format(cert.issuer_dn))
                    log.info('   Serial: {}'.format(cert.serial_number))
                    log.info('   Valid from: {}'.format(cert.valid_from))
                    log.info('   Valid to: {}'.format(cert.valid_to))

                    try:
                        signed_data.verify()
                        log.info('Signature: valid')
                    except Exception as e:
                        log.warning('Signature: invalid')
                        log.warning('{}'.format(e))
            except Exception as e:
                log.error('Error while parsing:')
                log.error('{}'.format(e))

    def run(self):
        self.compile_time_scan()

        self.pdb_scan()

        self.cert_scan()
        
        self.peid_scan()
