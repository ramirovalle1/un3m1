from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
server = Server('10.10.100.179', port=389, get_info=ALL)
conn = Connection(server, 'uid=zimbra,cn=admins,cn=zimbra', 'R4gHi7IF', auto_bind=True)
# conn = Connection(server, 'ou=people,dc=unemi,dc=edu,dc=ec', '', auto_bind=False)

# person = ObjectDef('person', conn)
# r = Reader(conn, person,'ou=people,dc=unemi,dc=edu,dc=ec')
# print(r)
# print('**************************')
# person+='uid'
# print(r)

# conn = Connection(server, 'ou=people,dc=unemi,dc=edu,dc=ec', '', auto_bind=False)

# busqueda
# conn.search('uid=cloyolar,ou=people,dc=unemi,dc=edu,dc=ec','(objectclass=person)')
# print (conn.entries)

# add
# conn.add('cn=pruebapython,ou=people,dc=unemi,dc=edu,dc=ec', 'inetOrgPerson', {'givenName':'xxx xxx', 'sn':'ZUNIGA PICO'})
# conn.add('cn=pruebapython,dc=unemi,dc=edu,dc=ec', 'inetOrgPerson', {'displayName':'xx xx xx xx', 'givenName':'xx xx', 'sn': 'xx xx', 'zimbraPrefFromDisplay':'xx xx xx xx'})
# conn.add('cn=pruebapython,ou=people,dc=unemi,dc=edu,dc=ec,uid=pruebapython@unemi.edu.ec,userPassword=123456', 'inetOrgPerson',  {'cn':'pruebapython@unemi.edu.ec', 'description':'xx xx', 'objectClass':'person', 'sn':'xx xx', 'userPassword':'123456'})
# conn.add('uid=pruebapython12,ou=people,dc=unemi,dc=edu,dc=ec', ['inetOrgPerson', 'zimbraAccount', 'amavisAccount'], {'givenName': 'Carlos', 'sn': 'Loyola', 'uid':'pruebapython12','cn': 'Carlos Loyola','mail':'pruebapython12@unemi.edu.ec','userPassword':123456})
#
# # perform the Add operation
# conn.add('cn=user1,ou=users,o=company', ['inetOrgPerson', 'posixGroup', 'top'], {'sn': 'user_sn', 'gidNumber': 0})
# # equivalent to
# conn.add('uid=pruebapython16,ou=people,dc=unemi,dc=edu,dc=ec', attributes={'zimbraMailStatus': 'enabled','objectClass':  ['inetOrgPerson', 'zimbraAccount', 'amavisAccount'], 'givenName': 'Carlos', 'sn': 'Loyola', 'uid':'pruebapython16','cn': 'Carlos Loyola','mail':'pruebapython16@unemi.edu.ec','userPassword':123456})
# conn.add('uid=pruebapython16,ou=people,dc=unemi,dc=edu,dc=ec', attributes={'zimbraMailStatus': 'enabled','objectClass':  ['inetOrgPerson', 'zimbraAccount', 'amavisAccount'], 'givenName': 'Carlos', 'sn': 'Loyola', 'uid':'pruebapython16','cn': 'Carlos Loyola','mail':'pruebapython16@unemi.edu.ec','userPassword':123456})
#
# conn.add('uid=pruebapython18,ou=people,dc=unemi,dc=edu,dc=ec', 'inetOrgPerson', {'objectClass':  ['inetOrgPerson', 'zimbraAccount', 'amavisAccount'],'givenName': 'Carlos', 'sn': 'Loyola', 'uid':'pruebapython18','cn': 'Carlos Loyola','mail':'pruebapython18@unemi.edu.ec','userPassword':123456})

# conn.search('uid=pruebapython9,ou=people,dc=unemi,dc=edu,dc=ec', '(objectclass=person)')
# print (conn.entries)


conn.modify('uid=pruebapython8,ou=people,dc=unemi,dc=edu,dc=ec', {'userPassword': [(MODIFY_REPLACE, [12])]})





# for entrada in conn.response:
#     print(entrada['dn'])

# conn.search(',ou=cloyolar,dc=unemi,dc=edu,dc=ec', '(cn=*)', attributes=['objectClass'])
# conn.add('cn=desarrollo,ou=ldap3-tutorial,dc=unemi,dc=edu,dc=ec', 'inetOrgPerson', {'givenName': 'Beatrix', 'sn': 'Young', 'departmentNumber': 'DEV', 'telephoneNumber': 1111})
# conn.entries




# from ldap3 import Server, Connection, ALL, NTLM
# server = Server('201.159.222.40', port=389, use_ssl=True, get_info=ALL)
# # conn = Connection(server, auto_bind=False)
# conn = Connection(server, 'uid=zimbra,cn=admins,cn=zimbra', 'R4gHi7IF', auto_bind=True)
# server.info
# server.schema


# from ldap3 import Server, Connection, ALL
# # from ldap3.core.exceptions import LDAPExceptionError, LDAPBindError, LDAPInvalidCredentialsResult, LDAPSizeLimitExceededResult
#
# s = Server('201.159.222.40', port=389, get_info=ALL)
# c = Connection(s, user='uid=zimbra,cn=admins,cn=zimbra', password='R4gHi7IF', auto_bind = True)
# c.start_tls()
# c.bind()
# c.search('dc=dominio,dc=com', '(uid=*)', attributes=['sn','cn', 'homeDirectory'], size_limit=0)
# for entrada in c.response:
#     print(entrada['dn'])
# #
# # ## The next lines will also need to be changed to support your search requirements and directory
# # baseDN = "ou=Customers, ou=Sales, o=anydomain.com"
# # searchScope = ldap.SCOPE_SUBTREE
# # ## retrieve all attributes - again adjust to your needs - see documentation for more options
# # retrieveAttributes = None
# # searchFilter = "cn=*jack*"
# #
# # try:
# # 	ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
# # 	result_set = []
# # 	while 1:
# # 		result_type, result_data = l.result(ldap_result_id, 0)
# # 		if (result_data == []):
# # 			break
# # 		else:
# # 			## here you don't have to append to a list
# # 			## you could do whatever you want with the individual entry
# # 			## The appending to list is just for illustration.
# # 			if result_type == ldap.RES_SEARCH_ENTRY:
# # 				result_set.append(result_data)
# # 	print result_set
# #
# # s = Server('201.159.222.40', get_info=ALL)  # define an unsecure LDAP server, requesting info on DSE and schema
# # c = Connection(s)
# # c.open()  # establish connection without performing any bind (equivalent to ANONYMOUS bind)
# # print(s.info.supported_sasl_mechanisms)
# # from ldap3 import Server, Connection, SUBTREE, ALL
# # total_entries = 0
# # server = Server('201.159.222.40', get_info=ALL)
# # c = Connection(server, user='uid=zimbra,cn=admins,cn=zimbra', password='R4gHi7IF', auto_bind = True)
# # entry_generator = c.extend.standard.paged_search(search_base = 'o=test', search_filter = '(objectClass=inetOrgPerson)', search_scope = SUBTREE, attributes = ['cn', 'givenName'],  paged_size = 5,generator=True)
# # for entry in entry_generator:
# #     total_entries += 1
# #     print(entry['dn'], entry['attributes'])
# # print('Total entries retrieved:', total_entries)