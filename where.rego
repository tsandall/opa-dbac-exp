package example

allow = true

# allow {
#     input.method = "GET"
#     input.path = ["posts"]
#     input.subject.user = data.posts.author
# }

# allow {
#     input.method = "GET"
#     input.path = ["posts"]
#     input.subject.departments[_] = data.posts.department
# }

# allow {
#     input.method = "GET"
#     input.path = ["posts"]
#     data.posts.department = "company"
# }

# allow {
#     input.method = "GET"
#     input.path = ["posts"]
#     user_in_hr
# }

# user_in_hr {
#     input.subject.departments[_] = "hr"
# }