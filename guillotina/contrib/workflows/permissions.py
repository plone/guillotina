from guillotina import configure


configure.permission("guillotina.ReviewContent", "Review content permission")
configure.permission("guillotina.RequestReview", "Request review content permission")

configure.grant(permission="guillotina.ReviewContent", role="guillotina.Reviewer")

configure.grant(permission="guillotina.ReviewContent", role="guillotina.Manager")

configure.grant(permission="guillotina.RequestReview", role="guillotina.Manager")

configure.grant(permission="guillotina.RequestReview", role="guillotina.Owner")

configure.grant(permission="guillotina.RequestReview", role="guillotina.ContainerAdmin")
