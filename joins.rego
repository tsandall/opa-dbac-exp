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
#     input.subject.user = data.posts_users.user
#     data.posts.id = data.posts_users.id
# }

# allow {
#     input.method = "GET"
#     input.path = ["posts"]
#     input.subject.departments[_] = data.posts_groups.group_name
#     data.posts.id = data.posts_groups.id
# }

# allow {
#     input.method = "GET"
#     input.path = ["posts"]
#     user_in_hr
# }

# user_in_hr {
#     input.subject.departments[_] = "hr"
# }
